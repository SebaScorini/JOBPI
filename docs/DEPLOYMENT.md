# DEPLOYMENT

## Usage Modes

JOBPI supports two documented ways to use the app:

- Local installation, where you run the backend and frontend yourself and provide your own `OPENROUTER_API_KEY` and `DSPY_MODEL`.
- Hosted usage at https://jobpi-app.vercel.app/.

## Prerequisites

- Python and Node.js toolchains for local execution.
- A PostgreSQL database for production deployments.
- OpenRouter API credentials for AI-enabled features.
- Vercel projects for backend and frontend hosting (if using Vercel).

## Local Run

Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Local endpoints:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`

## Environment Setup

- Copy the values from `.env.example` into a local `.env`.
- Set `DATABASE_URL` for production; SQLite is only a local fallback.
- Set `OPENROUTER_API_KEY` before using AI features.
- Set `VITE_API_URL` for the frontend so it points at the deployed backend.
- For local installation, you can also change `DSPY_MODEL` to your preferred model.

See [`docs/ENVIRONMENT.md`](ENVIRONMENT.md) for the full variable list.

Minimum production backend variables:

- `APP_ENV=production`
- `DATABASE_URL` (PostgreSQL)
- `SECRET_KEY`
- `OPENROUTER_API_KEY`

Recommended production variables:

- `REDIS_URL`
- `SENTRY_DSN`
- `FRONTEND_URL` or `CORS_ORIGINS` / `CORS_ORIGIN_REGEX`

## Vercel Deploy

1. Deploy the backend with the Python entrypoint in `api/index.py`.
2. Set `APP_ENV=production` in Vercel.
3. Set `DATABASE_URL` to the Supabase PostgreSQL connection string.
4. Set `SECRET_KEY` and `OPENROUTER_API_KEY` in the backend project.
5. Set `SENTRY_DSN` if you want runtime exceptions captured in Sentry.
6. Set `REDIS_URL` to enable shared rate limiting across multiple instances.
7. Set `FRONTEND_URL` or `CORS_ORIGINS` for the deployed frontend domain.
8. Set `VITE_API_URL` in the frontend project to the backend URL.
9. Make sure the backend environment installs `alembic`; startup now upgrades the schema to `head`.
10. Treat `VITE_SITE_URL` as optional deployment metadata only; the committed frontend runtime does not currently require it.

Suggested project split on Vercel:

- Backend project rooted at repository root using `api/index.py`.
- Frontend project rooted at `frontend/` with build command `npm run build`.

The repo includes `vercel.json` rewrites so requests are routed to the Python app.

## Supabase Setup

1. Create a Supabase project.
2. Copy the PostgreSQL connection string.
3. Use the PostgreSQL URL with `sslmode=require`.
4. Set that value as `DATABASE_URL` in the backend deployment.
5. Run `alembic upgrade head` or start the backend once so the migration bootstrap can apply the current schema.

Supabase notes:

- Use pooled production credentials and enforce SSL.
- Keep migration history in sync with deployed backend version.

## Operational Notes

- Production rate limits are stricter than local defaults.
- If `REDIS_URL` is missing, the backend falls back to the in-memory limiter.
- JWTs are issued with PyJWT and old custom-signed tokens still decode during the rollout window.
- Request body limits are enforced in the backend for uploads and long job descriptions.
- If `SENTRY_DSN` is configured, unexpected runtime exceptions are sent to Sentry with request metadata.
- If you use preview deployments, configure `CORS_ORIGIN_REGEX` to allow the preview domain pattern.
- The hosted app uses the production backend and production AI settings; local installs can override both.
- Schema changes are managed in Alembic revisions; see [`docs/MIGRATIONS.md`](MIGRATIONS.md).
- Existing databases that predate Alembic are stamped to the baseline revision automatically before newer revisions run.
- PostgreSQL keeps `NullPool` in production for serverless safety; local PostgreSQL uses a small `QueuePool` for faster repeat queries.

## Related Docs

- Environment variables: [`docs/ENVIRONMENT.md`](ENVIRONMENT.md)
- API contract: [`docs/API_REFERENCE.md`](API_REFERENCE.md)
- Architecture overview: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- Migration details: [`docs/MIGRATIONS.md`](MIGRATIONS.md)

## Post-Deploy Health Check

After each deployment:

1. Verify `GET /health` returns HTTP `200` and `{"status":"ok"}`.
2. Sign in and confirm `GET /auth/me` succeeds with a bearer token.
3. Exercise one database-backed flow such as listing CVs or jobs.
4. Run one AI-backed flow if `OPENROUTER_API_KEY` is configured.
5. Confirm logs include JSON request entries with a `trace_id`.

Use [`docs/HEALTH_CHECK.md`](HEALTH_CHECK.md) for the full checklist.

## Rollback

1. Re-deploy the previous known-good backend and frontend build in Vercel.
2. Keep environment variables aligned with that release, especially `DATABASE_URL`, `SECRET_KEY`, and `OPENROUTER_API_KEY`.
3. If a schema migration caused the issue, stop and verify the database state before attempting an Alembic downgrade.
4. Re-run the health-check flow after rollback to confirm recovery.

## Sprint 7 Pre-Deploy Verification

Run these checks before merging or deploying Sprint 7 changes:

```powershell
pytest -q
pytest --cov=app --cov-report=term-missing -q
python tests/benchmark.py
cd frontend
npm run test
npm run build
```

Expected outcomes:

- Backend suite passes.
- Coverage stays at or above the Sprint 6 target baseline.
- The benchmark script prints local latency baselines for `/health`, `/auth/login`, and paginated CV listing.
- Frontend component tests pass.
- The production frontend build completes successfully.
- Error responses keep the standardized `error.code`, `error.message`, `error.request_id`, and `error.timestamp` envelope.
