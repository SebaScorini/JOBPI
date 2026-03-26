from collections.abc import Generator

from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


def create_db_and_tables() -> None:
    import app.models  # noqa: F401

    _reset_legacy_dev_tables()
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


def _reset_legacy_dev_tables() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    legacy_tables = {"storedcv", "jobanalysis", "cvjobmatch"}
    new_tables = {"users", "cvs", "job_analyses", "cv_job_matches"}

    if not legacy_tables.issubset(table_names) or new_tables & table_names:
        return

    SQLModel.metadata.drop_all(
        engine,
        tables=[SQLModel.metadata.tables[name] for name in SQLModel.metadata.tables if name in new_tables],
    )
    with engine.begin() as connection:
        for table_name in legacy_tables:
            connection.exec_driver_sql(f"DROP TABLE IF EXISTS {table_name}")
