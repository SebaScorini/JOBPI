from collections.abc import Generator

from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings


settings = get_settings()
connect_args = (
    {"check_same_thread": False, "timeout": settings.sqlite_timeout_seconds}
    if settings.database_url.startswith("sqlite")
    else {}
)
engine = create_engine(settings.database_url, connect_args=connect_args)


def create_db_and_tables() -> None:
    import app.models  # noqa: F401

    _reset_legacy_dev_tables()
    SQLModel.metadata.create_all(engine)
    _ensure_job_tracking_columns()
    _ensure_job_cover_letter_columns()
    _ensure_cv_tags_column()
    _ensure_cv_library_summary_column()


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


def _ensure_job_tracking_columns() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "job_analyses" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("job_analyses")}

    with engine.begin() as connection:
        if "status" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE job_analyses ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'saved'"
            )
        if "applied_date" not in columns:
            connection.exec_driver_sql("ALTER TABLE job_analyses ADD COLUMN applied_date TIMESTAMP NULL")
        if "notes" not in columns:
            connection.exec_driver_sql("ALTER TABLE job_analyses ADD COLUMN notes TEXT NULL")


def _ensure_job_cover_letter_columns() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "job_analyses" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("job_analyses")}

    with engine.begin() as connection:
        if "generated_cover_letter" not in columns:
            connection.exec_driver_sql("ALTER TABLE job_analyses ADD COLUMN generated_cover_letter TEXT NULL")
        if "cover_letter_cv_id" not in columns:
            connection.exec_driver_sql("ALTER TABLE job_analyses ADD COLUMN cover_letter_cv_id INTEGER NULL")
        if "cover_letter_language" not in columns:
            connection.exec_driver_sql("ALTER TABLE job_analyses ADD COLUMN cover_letter_language VARCHAR(20) NULL")


def _ensure_cv_tags_column() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "cvs" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("cvs")}
    if "tags" in columns:
        return

    with engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE cvs ADD COLUMN tags JSON NOT NULL DEFAULT '[]'")


def _ensure_cv_library_summary_column() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "cvs" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("cvs")}
    if "library_summary" in columns:
        return

    with engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE cvs ADD COLUMN library_summary TEXT NOT NULL DEFAULT ''")
