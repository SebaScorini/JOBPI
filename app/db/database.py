from collections.abc import Generator

from sqlalchemy import inspect
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings


settings = get_settings()


def _build_connect_args() -> dict:
    if settings.is_sqlite:
        return {"check_same_thread": False, "timeout": settings.sqlite_timeout_seconds}
    return {}


engine_kwargs = {
    "connect_args": _build_connect_args(),
    "pool_pre_ping": not settings.is_sqlite,
}
if settings.is_postgres:
    engine_kwargs["poolclass"] = NullPool

engine = create_engine(settings.database_url, **engine_kwargs)


def create_db_and_tables() -> None:
    import app.models  # noqa: F401

    # SQLModel metadata remains the source of truth for table definitions.
    # SQLite-only compatibility helpers are kept for local legacy dev databases.
    if settings.is_sqlite:
        _reset_legacy_dev_tables()
    SQLModel.metadata.create_all(engine)
    if settings.is_sqlite:
        _ensure_schema_compatibility()


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


def _ensure_schema_compatibility() -> None:
    _ensure_job_tracking_columns()
    _ensure_job_cover_letter_columns()
    _ensure_cover_letter_cv_foreign_key()
    _ensure_cv_tags_column()
    _ensure_cv_library_summary_column()
    _ensure_foreign_key_indexes()


def _ensure_job_tracking_columns() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "job_analyses" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("job_analyses")}
    dialect_name = engine.dialect.name

    with engine.begin() as connection:
        if "status" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE job_analyses ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'saved'"
            )
        if "applied_date" not in columns:
            applied_date_type = "TIMESTAMPTZ" if dialect_name == "postgresql" else "TIMESTAMP"
            connection.exec_driver_sql(f"ALTER TABLE job_analyses ADD COLUMN applied_date {applied_date_type} NULL")
        if "notes" not in columns:
            connection.exec_driver_sql("ALTER TABLE job_analyses ADD COLUMN notes TEXT NULL")


def _ensure_job_cover_letter_columns() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "job_analyses" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("job_analyses")}
    dialect_name = engine.dialect.name

    with engine.begin() as connection:
        if "generated_cover_letter" not in columns:
            connection.exec_driver_sql("ALTER TABLE job_analyses ADD COLUMN generated_cover_letter TEXT NULL")
        if "cover_letter_cv_id" not in columns:
            if dialect_name == "postgresql":
                connection.exec_driver_sql(
                    "ALTER TABLE job_analyses "
                    "ADD COLUMN cover_letter_cv_id INTEGER NULL REFERENCES cvs (id) ON DELETE SET NULL"
                )
            else:
                connection.exec_driver_sql("ALTER TABLE job_analyses ADD COLUMN cover_letter_cv_id INTEGER NULL")
        if "cover_letter_language" not in columns:
            connection.exec_driver_sql("ALTER TABLE job_analyses ADD COLUMN cover_letter_language VARCHAR(20) NULL")


def _ensure_cover_letter_cv_foreign_key() -> None:
    if engine.dialect.name != "postgresql":
        return

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "job_analyses" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("job_analyses")}
    if "cover_letter_cv_id" not in columns:
        return

    foreign_keys = inspector.get_foreign_keys("job_analyses")
    has_cover_letter_fk = any(
        "cover_letter_cv_id" in (foreign_key.get("constrained_columns") or [])
        for foreign_key in foreign_keys
    )
    if has_cover_letter_fk:
        return

    with engine.begin() as connection:
        connection.exec_driver_sql(
            "UPDATE job_analyses "
            "SET cover_letter_cv_id = NULL, cover_letter_language = NULL, generated_cover_letter = NULL "
            "WHERE cover_letter_cv_id IS NOT NULL "
            "AND NOT EXISTS (SELECT 1 FROM cvs WHERE cvs.id = job_analyses.cover_letter_cv_id)"
        )
        connection.exec_driver_sql(
            "ALTER TABLE job_analyses "
            "ADD CONSTRAINT job_analyses_cover_letter_cv_id_fkey "
            "FOREIGN KEY (cover_letter_cv_id) REFERENCES cvs (id) ON DELETE SET NULL"
        )


def _ensure_cv_tags_column() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "cvs" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("cvs")}
    if "tags" in columns:
        return

    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            connection.exec_driver_sql("ALTER TABLE cvs ADD COLUMN tags JSONB NOT NULL DEFAULT '[]'::jsonb")
        else:
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


def _ensure_foreign_key_indexes() -> None:
    indexes_by_table = {
        "cvs": {"ix_cvs_user_id": "user_id"},
        "job_analyses": {
            "ix_job_analyses_user_id": "user_id",
            "ix_job_analyses_cover_letter_cv_id": "cover_letter_cv_id",
        },
        "cv_job_matches": {
            "ix_cv_job_matches_user_id": "user_id",
            "ix_cv_job_matches_cv_id": "cv_id",
            "ix_cv_job_matches_job_id": "job_id",
        },
    }

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table_name, indexes in indexes_by_table.items():
            if table_name not in existing_tables:
                continue

            existing_index_names = {index["name"] for index in inspect(engine).get_indexes(table_name)}
            for index_name, column_name in indexes.items():
                if index_name in existing_index_names:
                    continue
                connection.exec_driver_sql(
                    f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column_name})"
                )
