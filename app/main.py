from contextlib import asynccontextmanager
import logging
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

import sentry_sdk

from app.api.routes.auth import router as auth_router
from app.api.routes.cvs import router as cvs_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.matches import router as matches_router
from app.core.config import get_settings
from app.core.logging import bind_request_context, bind_user_context, reset_context, reset_user_context, setup_logging
from app.db.migration_runner import ensure_database_schema


logger = logging.getLogger(__name__)


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
            response = await call_next(request)
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
            logger.info(
                "request_end",
                extra={"status_code": response.status_code, "duration_ms": duration_ms},
            )
            response.headers["X-Trace-Id"] = trace_id
            return response
        finally:
            reset_user_context(user_context_token)
            reset_context(request_context_tokens)

    application.include_router(auth_router)
    application.include_router(cvs_router)
    application.include_router(jobs_router)
    application.include_router(matches_router)

    @application.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
