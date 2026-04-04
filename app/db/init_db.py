from app.core.config import get_settings
from app.db.migration_runner import ensure_database_schema


def main() -> None:
    ensure_database_schema()
    backend = "PostgreSQL" if get_settings().is_postgres else "SQLite"
    print(f"Initialized {backend} database schema via migrations.")


if __name__ == "__main__":
    main()
