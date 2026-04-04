# Migrations

JOBPI now treats Alembic as the source of truth for database schema changes.

## Files

- Config: [`alembic.ini`](../alembic.ini)
- Migration environment: [`app/db/migrations/env.py`](../app/db/migrations/env.py)
- Revisions: [`app/db/migrations/versions`](../app/db/migrations/versions)

## Common Commands

Create a migration:

```powershell
alembic revision -m "describe the change"
```

Autogenerate from the current SQLModel metadata:

```powershell
alembic revision --autogenerate -m "describe the change"
```

Apply migrations:

```powershell
alembic upgrade head
```

Rollback one step:

```powershell
alembic downgrade -1
```

Preview SQL without applying it:

```powershell
alembic upgrade head --sql
```

## Existing Databases

- Fresh databases should run `alembic upgrade head`.
- Databases that already have the JOBPI tables but no `alembic_version` row are stamped to `0001_baseline` during app startup, then upgraded to `head`.
- The startup bootstrap keeps old production data intact and applies only migrations that are newer than the stamped baseline.

## Workflow

1. Update SQLModel models.
2. Create a new Alembic revision.
3. Review the generated SQL carefully, especially constraints and indexes.
4. Run `alembic upgrade head` locally before opening a PR.
5. Deploy only after the migration has been tested against both SQLite and PostgreSQL if the change must support both.
