from collections.abc import Generator

from sqlalchemy.pool import NullPool, QueuePool, SingletonThreadPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings


settings = get_settings()


def _build_connect_args() -> dict:
    if settings.is_sqlite:
        return {"check_same_thread": False, "timeout": settings.sqlite_timeout_seconds}
    return {}


def _build_engine_kwargs() -> dict:
    engine_kwargs: dict[str, object] = {
        "connect_args": _build_connect_args(),
        "pool_pre_ping": not settings.is_sqlite,
    }

    if settings.is_sqlite:
        engine_kwargs["poolclass"] = SingletonThreadPool
        return engine_kwargs

    if settings.app_env == "production":
        # Vercel cold starts are safer with no long-lived PostgreSQL pool state.
        engine_kwargs["poolclass"] = NullPool
        return engine_kwargs

    engine_kwargs.update(
        {
            "poolclass": QueuePool,
            "pool_size": 5,
            "max_overflow": 10,
            "pool_recycle": 3600,
        }
    )
    return engine_kwargs


engine = create_engine(settings.database_url, **_build_engine_kwargs())


def create_db_and_tables() -> None:
    import app.models  # noqa: F401

    # Schema changes belong in Alembic migrations. This remains as a local fallback
    # for fresh SQLite databases when the migration runner is unavailable.
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
