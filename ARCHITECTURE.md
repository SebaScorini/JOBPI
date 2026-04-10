# ARCHITECTURE

JOBPI architecture is documented in detail in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

Summary:

- Frontend: React SPA in `frontend/`.
- Backend: FastAPI modular monolith in `app/`.
- Data: PostgreSQL in production, SQLite fallback in local development.
- Deployment: Vercel runtime with Supabase database.

See also:

- [`README.md`](README.md)
- [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md)
- [`API.md`](API.md)