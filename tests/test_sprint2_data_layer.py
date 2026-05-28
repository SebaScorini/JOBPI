import sys
import types
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, Session, create_engine

from app.models import JobAnalysis, User

from app.db import migration_runner


def test_ensure_database_schema_stamps_existing_schema_before_upgrade(monkeypatch):
    calls: list[tuple[str, str]] = []

    fake_alembic = types.ModuleType("alembic")
    fake_command = types.ModuleType("alembic.command")
    fake_config = types.ModuleType("alembic.config")

    class FakeConfig:
        def __init__(self, path: str) -> None:
            self.path = path
            self.options: dict[str, str] = {}

        def set_main_option(self, key: str, value: str) -> None:
            self.options[key] = value

    def stamp(config, revision: str) -> None:
        calls.append(("stamp", revision))

    def upgrade(config, revision: str) -> None:
        calls.append(("upgrade", revision))

    fake_command.stamp = stamp
    fake_command.upgrade = upgrade
    fake_config.Config = FakeConfig
    fake_alembic.command = fake_command
    fake_alembic.config = fake_config

    monkeypatch.setitem(sys.modules, "alembic", fake_alembic)
    monkeypatch.setitem(sys.modules, "alembic.command", fake_command)
    monkeypatch.setitem(sys.modules, "alembic.config", fake_config)

    class FakeInspector:
        def get_table_names(self):
            return ["users", "cvs", "job_analyses", "cv_job_matches"]

    monkeypatch.setattr(migration_runner, "inspect", lambda engine: FakeInspector())

    migration_runner.ensure_database_schema()

    assert calls == [("stamp", "0001_baseline"), ("upgrade", "head")]


def test_ensure_database_schema_only_upgrades_fresh_database(monkeypatch):
    calls: list[tuple[str, str]] = []

    fake_alembic = types.ModuleType("alembic")
    fake_command = types.ModuleType("alembic.command")
    fake_config = types.ModuleType("alembic.config")

    class FakeConfig:
        def __init__(self, path: str) -> None:
            self.path = path

        def set_main_option(self, key: str, value: str) -> None:
            return None

    def stamp(config, revision: str) -> None:
        calls.append(("stamp", revision))

    def upgrade(config, revision: str) -> None:
        calls.append(("upgrade", revision))

    fake_command.stamp = stamp
    fake_command.upgrade = upgrade
    fake_config.Config = FakeConfig
    fake_alembic.command = fake_command
    fake_alembic.config = fake_config

    monkeypatch.setitem(sys.modules, "alembic", fake_alembic)
    monkeypatch.setitem(sys.modules, "alembic.command", fake_command)
    monkeypatch.setitem(sys.modules, "alembic.config", fake_config)

    class FakeInspector:
        def get_table_names(self):
            return []

    monkeypatch.setattr(migration_runner, "inspect", lambda engine: FakeInspector())

    migration_runner.ensure_database_schema()

    assert calls == [("upgrade", "head")]


def test_ensure_database_schema_uses_postgres_advisory_lock(monkeypatch):
    calls: list[tuple[str, str]] = []
    executed_sql: list[str] = []

    fake_alembic = types.ModuleType("alembic")
    fake_command = types.ModuleType("alembic.command")
    fake_config = types.ModuleType("alembic.config")

    class FakeConfig:
        def __init__(self, path: str) -> None:
            self.path = path

        def set_main_option(self, key: str, value: str) -> None:
            return None

    def upgrade(config, revision: str) -> None:
        calls.append(("upgrade", revision))

    fake_command.stamp = lambda config, revision: None
    fake_command.upgrade = upgrade
    fake_config.Config = FakeConfig
    fake_alembic.command = fake_command
    fake_alembic.config = fake_config

    monkeypatch.setitem(sys.modules, "alembic", fake_alembic)
    monkeypatch.setitem(sys.modules, "alembic.command", fake_command)
    monkeypatch.setitem(sys.modules, "alembic.config", fake_config)

    monkeypatch.setattr(
        migration_runner,
        "get_settings",
        lambda: SimpleNamespace(is_postgres=True, database_url="postgresql://example"),
    )

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, statement, params):
            executed_sql.append(str(statement))
            assert params == {"lock_id": migration_runner.MIGRATION_LOCK_ID}

    class FakeEngine:
        def connect(self):
            return FakeConnection()

    class FakeInspector:
        def get_table_names(self):
            return ["alembic_version"]

    monkeypatch.setattr(migration_runner, "engine", FakeEngine())
    monkeypatch.setattr(migration_runner, "inspect", lambda engine: FakeInspector())

    migration_runner.ensure_database_schema()

    assert executed_sql == [
        "SELECT pg_advisory_lock(:lock_id)",
        "SELECT pg_advisory_unlock(:lock_id)",
    ]
    assert calls == [("upgrade", "head")]


def test_job_analysis_status_check_constraint_is_enforced():
    tmp_dir = Path.cwd() / ".tmp-tests"
    tmp_dir.mkdir(exist_ok=True)
    db_path = tmp_dir / f"status-check-{uuid4().hex}.db"
    engine = create_engine(f"sqlite:///{db_path.resolve().as_posix()}")

    try:
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            user = User(email="constraint@example.com", hashed_password="hashed")
            session.add(user)
            session.commit()
            session.refresh(user)

            invalid_job = JobAnalysis(
                user_id=user.id,
                title="Backend Engineer",
                company="Acme",
                description="desc",
                clean_description="desc",
                analysis_result={"summary": "ok"},
                status="invalid-status",
            )
            session.add(invalid_job)

            with pytest.raises(IntegrityError):
                session.commit()
    finally:
        engine.dispose()
        if db_path.exists():
            db_path.unlink()


def test_create_job_analysis_populates_legacy_follow_up_cache_column():
    from app.db import crud

    tmp_dir = Path.cwd() / ".tmp-tests"
    tmp_dir.mkdir(exist_ok=True)
    db_path = tmp_dir / f"legacy-follow-up-cache-{uuid4().hex}.db"
    engine = create_engine(f"sqlite:///{db_path.resolve().as_posix()}")

    try:
        SQLModel.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE job_analyses")
            connection.exec_driver_sql(
                """
                CREATE TABLE job_analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    company VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    clean_description TEXT NOT NULL,
                    analysis_result JSON NOT NULL,
                    is_saved BOOLEAN NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    applied_date DATETIME NULL,
                    notes TEXT NULL,
                    generated_cover_letter TEXT NULL,
                    cover_letter_cv_id INTEGER NULL,
                    cover_letter_language VARCHAR(20) NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    deleted_at DATETIME NULL,
                    linkedin_outreach_cache JSON NOT NULL,
                    linkedin_follow_up_cache JSON NOT NULL
                )
                """
            )

        with Session(engine) as session:
            user = User(email="legacy-cache@example.com", hashed_password="hashed")
            session.add(user)
            session.commit()
            session.refresh(user)

            job = crud.create_job_analysis(
                session,
                user_id=user.id,
                title="Backend Engineer",
                company="Acme",
                description="Build APIs",
                clean_description="Build APIs",
                analysis_result={"summary": "ok"},
            )

            assert job.id is not None

            row = session.connection().exec_driver_sql(
                "SELECT linkedin_outreach_cache, linkedin_follow_up_cache FROM job_analyses WHERE id = ?",
                (job.id,),
            ).one()
            assert row[0] == "{}"
            assert row[1] == "{}"
    finally:
        engine.dispose()
        if db_path.exists():
            db_path.unlink()
