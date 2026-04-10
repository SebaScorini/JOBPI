# PROJECT CONTEXT

JOBPI is an AI-assisted job application workspace with a React frontend and a FastAPI backend. It helps authenticated users upload CVs, analyze job descriptions, compare CV fit, generate cover letters, and track application progress.

## What the Project Does

- Centralizes CV library management, job analysis, and application tracking.
- Provides AI-assisted fit analysis and cover-letter generation.
- Supports authenticated, user-scoped workflows end to end.

## Architecture Overview

- Frontend: Vite + React SPA in `frontend/`
- Backend: FastAPI app in `app/`
- Vercel entrypoint: `api/index.py`
- Database: PostgreSQL in production, SQLite fallback for local development
- AI provider path: DSPy configured against OpenRouter

## Backend Role

- Owns authentication, request validation, rate limiting, and orchestration.
- Persists users, CVs, jobs, and match outputs.
- Exposes REST endpoints used by the frontend.

## Frontend Role

- Handles routing, forms, dashboards, and rendering of backend responses.
- Uses one API client layer in `frontend/src/services/api.ts`.
- Stores bearer token and attaches it to protected calls.

## Database Role

- Uses PostgreSQL in production and SQLite for local fallback.
- Stores user accounts, uploaded CVs, analyzed jobs, and CV-job matches.

## Auth Flow

1. Register or log in through `/auth`.
2. Backend returns a bearer token.
3. Frontend sends token on protected requests.
4. Backend resolves current user and enforces ownership checks.

## External Services

- OpenRouter for model inference.
- Supabase for hosted PostgreSQL.
- Vercel for deployment.

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
