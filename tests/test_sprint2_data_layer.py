import sys
import types

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
