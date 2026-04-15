import json
import logging
from typing import Any
from urllib import error, parse, request

from app.core.config import get_settings


logger = logging.getLogger(__name__)

CV_PDF_BUCKET = "cv-pdfs"


class SupabaseStorageError(RuntimeError):
    pass


def build_cv_storage_path(*, user_id: int, cv_id: int) -> str:
    return f"{user_id}/{cv_id}.pdf"


class SupabaseStorageService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def upload_cv_pdf(self, *, path: str, file_bytes: bytes, upsert: bool = True) -> None:
        self._require_configuration()
        encoded_path = _encode_object_path(path)
        headers = {
            "Content-Type": "application/pdf",
            "x-upsert": "true" if upsert else "false",
        }
        self._request(
            method="POST",
            path=f"/storage/v1/object/{CV_PDF_BUCKET}/{encoded_path}",
            data=file_bytes,
            headers=headers,
        )

    def create_signed_download_url(self, *, path: str, expires_in: int = 60) -> str:
        self._require_configuration()
        encoded_path = _encode_object_path(path)
        payload = self._request(
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
        self._request(
            method="DELETE",
            path=f"/storage/v1/object/{CV_PDF_BUCKET}",
            json_body={"prefixes": [path]},
        )

    def _require_configuration(self) -> None:
        if not self.settings.supabase_url:
            raise SupabaseStorageError("SUPABASE_URL is not configured.")
        if not self.settings.supabase_service_role_key:
            raise SupabaseStorageError("SUPABASE_SERVICE_ROLE_KEY is not configured.")

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
            detail = exc.read().decode("utf-8", errors="replace")
            logger.warning("supabase_storage_http_error status=%s body=%s", exc.code, detail)
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


_service: SupabaseStorageService | None = None


def get_supabase_storage_service() -> SupabaseStorageService:
    global _service
    if _service is None:
        _service = SupabaseStorageService()
    return _service
