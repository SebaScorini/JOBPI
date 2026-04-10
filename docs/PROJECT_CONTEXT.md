# PROJECT CONTEXT

## What the Project Does

JOBPI is an AI-assisted job application workspace for managing CVs, analyzing jobs, comparing fit, generating cover letters, and tracking application progress in one place.

## Architecture Overview

JOBPI uses a modular monolith architecture:

- React SPA frontend for user interaction.
- FastAPI backend for transport, auth, validation, and orchestration.
- SQLModel-based persistence layer for users, CVs, job analyses, and matches.
- DSPy plus OpenRouter for AI-assisted generation and analysis.

Primary interfaces:

- End-user browser UI served by the frontend app.
- JSON REST API exposed by the FastAPI backend.
- PostgreSQL-compatible data layer (Supabase in production).

## Backend Role

- Owns authentication and authorization.
- Validates uploads and request sizes.
- Persists and reuses job analysis, CV analysis, and cover-letter data.
- Applies rate limits and user scoping on protected operations.

## Frontend Role

- Handles routing, dashboards, forms, and data presentation.
- Uses `frontend/src/services/api.ts` as the single API client.
- Stores and reuses the bearer token for authenticated requests.
- Applies user-level UX flows for CV upload, job analysis, matching, and application tracking.

## Database Role

- Production uses PostgreSQL, typically through Supabase.
- Development can fall back to SQLite when `DATABASE_URL` is omitted.
- Core tables are `users`, `cvs`, `job_analyses`, and `cv_job_matches`.
- Data ownership is enforced per user in backend business logic.

## Auth Flow

1. User registers or logs in.
2. Backend verifies credentials and returns a bearer token.
3. Frontend stores the token locally.
4. Protected requests attach the token in `Authorization`.
5. Backend resolves the current user and enforces row-level ownership in application code.

## External Services

- OpenRouter for AI inference.
- Supabase for hosted PostgreSQL.
- Vercel for deployment.

## Where to Continue

- API contract details: [`docs/API_REFERENCE.md`](API_REFERENCE.md)
- Runtime architecture and flows: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- Deployment and operations: [`docs/DEPLOYMENT.md`](DEPLOYMENT.md)
- Full environment variable reference: [`docs/ENVIRONMENT.md`](ENVIRONMENT.md)

## Related Docs

- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- [`docs/API_REFERENCE.md`](API_REFERENCE.md)
- [`docs/DEPLOYMENT.md`](DEPLOYMENT.md)
- [`docs/ENVIRONMENT.md`](ENVIRONMENT.md)