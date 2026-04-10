from __future__ import annotations

import logging
from contextlib import contextmanager

from sqlalchemy import inspect, text

from app.core.config import BASE_DIR, get_settings
from app.db.database import create_db_and_tables, engine


logger = logging.getLogger(__name__)

ALEMBIC_INI_PATH = BASE_DIR / "alembic.ini"
APP_TABLES = {"users", "cvs", "job_analyses", "cv_job_matches"}
BASELINE_REVISION = "0001_baseline"
MIGRATION_LOCK_ID = 90210017


@contextmanager
def _suppress_alembic_info_logs() -> None:
    logger_names = ("alembic", "alembic.runtime.migration", "alembic.runtime.plugins")
    previous_levels = {name: logging.getLogger(name).level for name in logger_names}
    try:
        for name in logger_names:
            logging.getLogger(name).setLevel(logging.WARNING)
        yield
    finally:
        for name, level in previous_levels.items():
            logging.getLogger(name).setLevel(level)


@contextmanager
def _postgres_migration_lock() -> None:
    settings = get_settings()
    if not settings.is_postgres:
        yield
        return

    with engine.connect() as connection:
        logger.info("db_migrations_lock_acquire lock_id=%s", MIGRATION_LOCK_ID)
        connection.execute(text("SELECT pg_advisory_lock(:lock_id)"), {"lock_id": MIGRATION_LOCK_ID})
        try:
            yield
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": MIGRATION_LOCK_ID})
            logger.info("db_migrations_lock_release lock_id=%s", MIGRATION_LOCK_ID)


def ensure_database_schema() -> None:
    try:
        from alembic import command
        from alembic.config import Config
    except ImportError:
        logger.warning("db_migrations_unavailable fallback=create_all")
        create_db_and_tables()
        return

    if not ALEMBIC_INI_PATH.exists():
        logger.warning("db_migrations_config_missing path=%s fallback=create_all", ALEMBIC_INI_PATH)
        create_db_and_tables()
        return

    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str((BASE_DIR / "app" / "db" / "migrations").resolve()))
    config.set_main_option("sqlalchemy.url", get_settings().database_url)
    config_attributes = getattr(config, "attributes", None)
    if config_attributes is None:
        config_attributes = {}
        setattr(config, "attributes", config_attributes)
    config_attributes["skip_logging_config"] = True

    with _postgres_migration_lock():
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        if "alembic_version" not in existing_tables and APP_TABLES.issubset(existing_tables):
            # Older local databases can already contain the app tables without an Alembic
            # version row. Stamping the known baseline keeps startup from replaying the
            # initial schema creation against a database that is already populated.
            logger.info("db_migrations_stamp baseline=%s", BASELINE_REVISION)
            command.stamp(config, BASELINE_REVISION)

        logger.info("db_migrations_upgrade revision=head")
        with _suppress_alembic_info_logs():
            command.upgrade(config, "head")
