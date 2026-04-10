# PROJECT CONTEXT

JOBPI is an AI-assisted job application workspace with a React frontend and a FastAPI backend. It helps authenticated users upload CVs, analyze job descriptions, compare multiple CVs against a role, generate cover letters, and track application progress over time.

## Runtime Shape

- Frontend: Vite + React SPA in `frontend/`
- Backend: FastAPI app in `app/`
- Vercel entrypoint: `api/index.py`
- Database: PostgreSQL in production, SQLite fallback for local development
- AI provider path: DSPy configured against OpenRouter

## Core Product Flows

1. Register or log in through `/auth`.
2. Upload one or more CV PDFs through `/cvs`.
3. Analyze a job description through `/jobs/analyze`.
4. Match a selected CV to a job, compare CVs, or generate a cover letter.
5. Track job status, saved state, and notes from the dashboard UI.

## Safety-Critical Boundaries

- Auth is JWT-based and all user-owned records are filtered by `user_id`.
- Request size checks and rate limiting protect AI-heavy endpoints from abuse.
- Secrets and deployment settings are loaded from environment variables in the backend only.
- Production startup expects a real `SECRET_KEY` and a PostgreSQL `DATABASE_URL`.

## Local Development Notes

- `uvicorn app.main:app --reload` starts the backend locally.
- `frontend/src/services/api.ts` uses `VITE_API_URL` when set and falls back to `http://localhost:8000` for local browser sessions on `localhost`.
- Docker resources live under `.config/docker/`.
- The backend runs Alembic migrations on startup when available, with a conservative local fallback for fresh SQLite setups.

## Canonical Docs

- [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md)
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)
- [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)
