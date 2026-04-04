from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import inspect

from app.core.config import BASE_DIR, get_settings
from app.db.database import create_db_and_tables, engine


logger = logging.getLogger(__name__)

ALEMBIC_INI_PATH = BASE_DIR / "alembic.ini"
APP_TABLES = {"users", "cvs", "job_analyses", "cv_job_matches"}
BASELINE_REVISION = "0001_baseline"


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

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    if "alembic_version" not in existing_tables and APP_TABLES.issubset(existing_tables):
        logger.info("db_migrations_stamp baseline=%s", BASELINE_REVISION)
        command.stamp(config, BASELINE_REVISION)

    logger.info("db_migrations_upgrade revision=head")
    command.upgrade(config, "head")
