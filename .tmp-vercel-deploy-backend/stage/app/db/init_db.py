from app.core.config import get_settings
from app.db.database import create_db_and_tables


def main() -> None:
    create_db_and_tables()
    backend = "PostgreSQL" if get_settings().is_postgres else "SQLite"
    print(f"Initialized {backend} database schema.")


if __name__ == "__main__":
    main()
