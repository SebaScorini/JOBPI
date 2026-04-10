# Project Structure

This guide reflects the current repository layout. It is meant to help maintainers find the canonical source for runtime code, deployment config, tests, and docs without guessing.

## Top Level

```text
JOBPI/
|-- .config/         Configuration templates and Docker resources
|-- .scripts/        Local helper scripts
|-- api/             Vercel Python entrypoint
|-- app/             Backend FastAPI application
|-- docs/            Canonical project documentation
|-- frontend/        React + Vite frontend
|-- tests/           Backend test suite
|-- design-system/   Design references and guidance assets
|-- README.md        Primary onboarding document
|-- PROJECT_CONTEXT.md
|-- Makefile
|-- alembic.ini
|-- vercel.json
```

## Backend

`app/` contains the production backend code.

- `app/main.py`: FastAPI app creation, middleware, exception handling, startup lifecycle
- `app/api/routes/`: HTTP routes for auth, CVs, jobs, and matches
- `app/core/`: settings, logging, security, validation, AI helpers, and rate limiting
- `app/db/`: engine setup, CRUD helpers, migration runner, and Alembic migrations
- `app/dependencies/`: FastAPI dependencies such as current-user resolution
- `app/models/`: SQLModel entities
- `app/schemas/`: request and response models
- `app/services/`: business workflows for uploads, analysis, matching, and cover letters

## Frontend

`frontend/` contains the user-facing web app.

- `frontend/src/pages/`: route-level screens
- `frontend/src/components/`: shared UI components
- `frontend/src/context/`: auth, language, theme, and toast state
- `frontend/src/services/api.ts`: typed API client and auth token wiring
- `frontend/src/types/`: shared frontend types
- `frontend/src/i18n/`: translations
- `frontend/public/`: static assets

Build output such as `frontend/dist/` and dependency installs such as `frontend/node_modules/` are local artifacts and should not be treated as source.

## Configuration and Deployment

- `.config/docker/`: Docker Compose, backend/frontend container images, and nginx config
- `.config/.env.docker`: Docker-oriented environment template
- `vercel.json`: root Vercel routing for the backend deployment
- `frontend/vercel.json`: frontend-specific Vercel config for the SPA
- `api/index.py`: Vercel adapter that exposes the FastAPI app
- `alembic.ini`: Alembic configuration used by the backend migration runner

## Tests and Docs

- `tests/`: backend pytest suite, fixtures, and benchmark smoke script
- `tests/README.md`: how to run the test suite locally
- `docs/`: canonical architecture, API, environment, deployment, Docker, and health-check docs
- Root files such as `API.md`, `ARCHITECTURE.md`, and `CONTEXT.md`: short signposts that point to the canonical documentation under `docs/`

## Maintenance Notes

- Treat `app/main.py`, `api/index.py`, `vercel.json`, env handling, auth code, and rate limiting as runtime-critical.
- Avoid deleting files just because they look unused; confirm imports, scripts, and deployment references first.
- Local cache folders, coverage outputs, SQLite scratch databases, and test/build artifacts are workspace hygiene items, not source files.
