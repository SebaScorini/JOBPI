from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

import sentry_sdk

from app.api.routes.auth import router as auth_router
from app.api.routes.cvs import router as cvs_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.matches import router as matches_router
from app.core.config import get_settings
from app.core.logging import bind_request_context, bind_user_context, reset_context, reset_user_context, setup_logging
from app.db.migration_runner import ensure_database_schema
from app.schemas.error import ErrorResponse


logger = logging.getLogger(__name__)
MAX_REQUEST_BYTES = 10 * 1024 * 1024
RESPONSE_WARNING_BYTES = 5 * 1024 * 1024


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_database_schema()
    yield


def _request_body_size(request: Request) -> int | None:
    raw_value = request.headers.get("content-length")
    if not raw_value:
        return None
    try:
        return int(raw_value)
    except ValueError:
        return None


def _capture_exception_with_sentry(request: Request, exc: Exception) -> None:
    if not sentry_sdk.is_initialized():
        return

    with sentry_sdk.push_scope() as scope:
        user_id = getattr(request.state, "user_id", None)
        user_email = getattr(request.state, "user_email", None)
        if user_id or user_email:
            scope.user = {"id": user_id, "email": user_email}
        scope.set_tag("trace_id", getattr(request.state, "trace_id", None))
        scope.set_context(
            "request",
            {
                "path": request.url.path,
                "method": request.method,
                "body_size": _request_body_size(request),
            },
        )
        sentry_sdk.capture_exception(exc)


def _setup_sentry() -> None:
    settings = get_settings()
    if not settings.sentry_dsn or sentry_sdk.is_initialized():
        return

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
    )


def _error_payload(request: Request, code: str, message: str, *, timestamp: datetime | None = None) -> dict:
    payload = ErrorResponse(
        error={
            "code": code,
            "message": message,
            "request_id": getattr(request.state, "trace_id", None),
            "timestamp": timestamp or datetime.now(timezone.utc),
        }
    )
    return payload.model_dump(mode="json")


def _http_error_code(request: Request, exc: HTTPException) -> str:
    detail = str(exc.detail).lower() if exc.detail is not None else ""
    path = request.url.path.lower()

    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return "ERR_UNAUTHORIZED"
    if exc.status_code == status.HTTP_403_FORBIDDEN:
        return "ERR_FORBIDDEN"
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        if "/cvs" in path or "cv " in detail:
            return "ERR_CV_NOT_FOUND"
        if "/jobs" in path or "job " in detail:
            return "ERR_JOB_NOT_FOUND"
        if "/matches" in path or "match " in detail:
            return "ERR_MATCH_NOT_FOUND"
        return "ERR_NOT_FOUND"
    if exc.status_code == status.HTTP_409_CONFLICT:
        return "ERR_CONFLICT"
    if exc.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE:
        return "ERR_PAYLOAD_TOO_LARGE"
    if exc.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        return "ERR_VALIDATION"
    if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        return "ERR_RATE_LIMIT"
    if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
        return "ERR_SERVICE_UNAVAILABLE"
    return f"ERR_HTTP_{exc.status_code}"


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()
    _setup_sentry()
    application = FastAPI(
        title="JOBPI",
        version="0.2.0",
        description="Authenticated AI job analysis backend with user-scoped CVs, jobs, and matches.",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        max_age=settings.cors_max_age_seconds,
    )

    @application.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id

        request_context_tokens = bind_request_context(
            trace_id=trace_id,
            path=request.url.path,
            method=request.method,
        )
        user_context_token = bind_user_context(getattr(request.state, "user_id", None))

        started_at = time.perf_counter()
        logger.info("request_start")

        try:
            request_size = _request_body_size(request)
            if request_size is not None and request_size > MAX_REQUEST_BYTES:
                duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
                logger.warning(
                    "request_rejected",
                    extra={"status_code": status.HTTP_413_CONTENT_TOO_LARGE, "duration_ms": duration_ms},
                )
                response = JSONResponse(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    content=_error_payload(
                        request,
                        "ERR_PAYLOAD_TOO_LARGE",
                        "Request body exceeds the 10 MB API limit.",
                    ),
                )
                response.headers["X-Trace-Id"] = trace_id
                return response
            response = await call_next(request)
        except HTTPException as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.warning(
                "request_rejected",
                extra={"status_code": exc.status_code, "duration_ms": duration_ms},
            )
            raise
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "request_exception",
                extra={"status_code": 500, "duration_ms": duration_ms},
            )
            _capture_exception_with_sentry(request, exc)
            raise
        else:
            if getattr(request.state, "user_id", None):
                bind_user_context(request.state.user_id)
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            response_size = getattr(response, "body", None)
            if response_size is not None and len(response.body) > RESPONSE_WARNING_BYTES:
                logger.warning(
                    "response_size_warning",
                    extra={"status_code": response.status_code, "response_bytes": len(response.body)},
                )
            elif (content_length := response.headers.get("content-length")):
                try:
                    if int(content_length) > RESPONSE_WARNING_BYTES:
                        logger.warning(
                            "response_size_warning",
                            extra={"status_code": response.status_code, "response_bytes": int(content_length)},
                        )
                except ValueError:
                    pass
            logger.info(
                "request_end",
                extra={"status_code": response.status_code, "duration_ms": duration_ms},
            )
            response.headers["X-Trace-Id"] = trace_id
            return response
        finally:
            reset_user_context(user_context_token)
            reset_context(request_context_tokens)

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        code = _http_error_code(request, exc)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(request, code, str(exc.detail)),
            headers=exc.headers or None,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        first_error = exc.errors()[0] if exc.errors() else {}
        message = str(first_error.get("msg") or "Request validation failed.")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_payload(request, "ERR_VALIDATION", message),
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload(request, "ERR_INTERNAL_SERVER_ERROR", "An unexpected error occurred."),
        )

    application.include_router(auth_router)
    application.include_router(cvs_router)
    application.include_router(jobs_router)
    application.include_router(matches_router)

    @application.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
