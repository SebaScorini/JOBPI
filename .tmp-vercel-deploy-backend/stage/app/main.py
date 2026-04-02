from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.cvs import router as cvs_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.matches import router as matches_router
from app.core.config import get_settings
from app.db.database import create_db_and_tables


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
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

    application.include_router(auth_router)
    application.include_router(cvs_router)
    application.include_router(jobs_router)
    application.include_router(matches_router)

    @application.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
