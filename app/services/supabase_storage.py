import json
import logging
from typing import Any
from urllib import error, parse, request

from app.core.config import get_settings
from app.core.service_circuit_breaker import (
    ServiceCircuitBreaker,
    ServiceCircuitBreakerConfig,
    ServiceCircuitBreakerOpenError,
)


logger = logging.getLogger(__name__)

CV_PDF_BUCKET = "cv-pdfs"


class SupabaseStorageError(RuntimeError):
    pass


class SupabaseStorageUnavailableError(SupabaseStorageError):
    """Raised when the storage circuit breaker is open."""

    pass


def _is_retryable_storage_error(exc: Exception) -> bool:
    """Determine whether a storage error is worth retrying."""
    if isinstance(exc, error.HTTPError):
        return exc.code in {500, 502, 503, 504, 429}
    if isinstance(exc, (error.URLError, ConnectionError, TimeoutError)):
        return True
    if isinstance(exc, SupabaseStorageError):
        cause = exc.__cause__
        if isinstance(cause, error.HTTPError):
            return cause.code in {500, 502, 503, 504, 429}
        return isinstance(cause, (error.URLError, ConnectionError, TimeoutError))
    return False


class SupabaseStorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._circuit_breaker = ServiceCircuitBreaker(
            "supabase_storage",
            ServiceCircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout_seconds=30.0,
                retries=2,
                backoff_base_ms=100,
                max_backoff_ms=2000,
            ),
        )

    def is_available(self) -> bool:
        """Check if the storage service circuit breaker is healthy."""
        return self._circuit_breaker.is_available

    def upload_cv_pdf(self, *, path: str, file_bytes: bytes, upsert: bool = True) -> None:
        self._require_configuration()
        encoded_path = _encode_object_path(path)
        headers = {
            "Content-Type": "application/pdf",
            "x-upsert": "true" if upsert else "false",
        }
        self._protected_request(
            method="POST",
            path=f"/storage/v1/object/{CV_PDF_BUCKET}/{encoded_path}",
            data=file_bytes,
            headers=headers,
        )

    def create_signed_download_url(self, *, path: str, expires_in: int = 60) -> str:
        self._require_configuration()
        encoded_path = _encode_object_path(path)
        payload = self._protected_request(
            method="POST",
            path=f"/storage/v1/object/sign/{CV_PDF_BUCKET}/{encoded_path}",
            json_body={"expiresIn": expires_in},
        )
        token_path = payload.get("signedURL") or payload.get("signedUrl")
        if not isinstance(token_path, str) or not token_path.strip():
            raise SupabaseStorageError("Supabase Storage did not return a signed URL.")
        if token_path.startswith("http://") or token_path.startswith("https://"):
            return token_path
        return f"{self.settings.supabase_url.rstrip('/')}/storage/v1{token_path}"

    def delete_cv_pdf(self, *, path: str) -> None:
        self._require_configuration()
        self._protected_request(
            method="DELETE",
            path=f"/storage/v1/object/{CV_PDF_BUCKET}",
            json_body={"prefixes": [path]},
        )

    def _require_configuration(self) -> None:
        if not self.settings.supabase_url:
            raise SupabaseStorageError("SUPABASE_URL is not configured.")
        if not self.settings.supabase_service_role_key:
            raise SupabaseStorageError("SUPABASE_SERVICE_ROLE_KEY is not configured.")

    def _protected_request(self, **kwargs: Any) -> dict[str, Any]:
        """Execute a storage request through the circuit breaker."""
        try:
            return self._circuit_breaker.call(
                self._request,
                retryable=_is_retryable_storage_error,
                **kwargs,
            )
        except ServiceCircuitBreakerOpenError:
            raise SupabaseStorageUnavailableError(
                "Supabase Storage is temporarily unavailable. Please try again shortly."
            )

    def _request(
        self,
        *,
        method: str,
        path: str,
        data: bytes | None = None,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        body = data
        request_headers = {
            "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
            "apikey": self.settings.supabase_service_role_key,
        }
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        if headers:
            request_headers.update(headers)

        req = request.Request(
            url=f"{self.settings.supabase_url.rstrip('/')}{path}",
            data=body,
            headers=request_headers,
            method=method,
        )

        try:
            with request.urlopen(req, timeout=20) as response:
                payload = response.read()
        except error.HTTPError as exc:
            logger.warning("supabase_storage_http_error status=%s", exc.code)
            raise SupabaseStorageError(f"Supabase Storage request failed with status {exc.code}.") from exc
        except error.URLError as exc:
            raise SupabaseStorageError("Could not reach Supabase Storage.") from exc

        if not payload:
            return {}
        try:
            return json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            return {}


def _encode_object_path(path: str) -> str:
    return parse.quote(path.lstrip("/"), safe="/")


def build_cv_storage_path(*, user_id: int, cv_id: int) -> str:
    """Build a deterministic storage path for a CV PDF."""
    return f"{user_id}/{cv_id}.pdf"


_service: SupabaseStorageService | None = None


def get_supabase_storage_service() -> SupabaseStorageService:
    global _service
    if _service is None:
        _service = SupabaseStorageService()
    return _service
