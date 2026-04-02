# DEPLOYMENT

## Usage Modes

JOBPI supports two documented ways to use the app:

- Local installation, where you run the backend and frontend yourself and provide your own `OPENROUTER_API_KEY` and `DSPY_MODEL`.
- Hosted usage at https://jobpi-app.vercel.app/.

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

## Environment Setup

- Copy the values from `.env.example` into a local `.env`.
- Set `DATABASE_URL` for production; SQLite is only a local fallback.
- Set `OPENROUTER_API_KEY` before using AI features.
- Set `VITE_API_URL` for the frontend so it points at the deployed backend.
- For local installation, you can also change `DSPY_MODEL` to your preferred model.

See [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) for the full variable list.

## Vercel Deploy

1. Deploy the backend with the Python entrypoint in `api/index.py`.
2. Set `APP_ENV=production` in Vercel.
3. Set `DATABASE_URL` to the Supabase PostgreSQL connection string.
4. Set `SECRET_KEY` and `OPENROUTER_API_KEY` in the backend project.
5. Set `FRONTEND_URL` or `CORS_ORIGINS` for the deployed frontend domain.
6. Set `VITE_API_URL` in the frontend project to the backend URL.

The repo includes `vercel.json` rewrites so requests are routed to the Python app.

## Supabase Setup

1. Create a Supabase project.
2. Copy the PostgreSQL connection string.
3. Use the PostgreSQL URL with `sslmode=require`.
4. Set that value as `DATABASE_URL` in the backend deployment.
5. Start the backend once so the schema is created automatically.

## Operational Notes

- Production rate limits are stricter than local defaults.
- Request body limits are enforced in the backend for uploads and long job descriptions.
- If you use preview deployments, configure `CORS_ORIGIN_REGEX` to allow the preview domain pattern.
- The hosted app uses the production backend and production AI settings; local installs can override both.