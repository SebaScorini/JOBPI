# JOBPI

AI-powered job application assistant for CV optimization, role matching, and application tracking.

## Overview

JOBPI helps users analyze job descriptions, manage a personal CV library, compare CVs against a role, generate cover letters, and track applications in one workflow. The backend handles authentication, persistence, and AI-assisted analysis; the frontend provides the dashboard and job-management experience.

## Tech Stack

Backend: FastAPI, SQLModel, PostgreSQL on Supabase, SQLite fallback for local development, DSPy, OpenRouter.

Frontend: React, TypeScript, Vite, Tailwind CSS, React Router.

## Features

- JWT authentication
- Single and batch CV upload
- CV summaries and tags
- Job description analysis
- CV-to-job matching and comparison
- Tailored cover letter generation
- Job tracking with status and notes
- English/Spanish UI support

## Quick Start

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

## Deployment

The backend is deployed on Vercel through the Python entrypoint in `api/index.py`. Production should use Supabase PostgreSQL via `DATABASE_URL`, `APP_ENV=production`, a strong `SECRET_KEY`, and a valid `OPENROUTER_API_KEY`.

The frontend should be built with `VITE_API_URL` pointing to the deployed backend. `VITE_SITE_URL` is recommended for production canonical URLs.

See the detailed guides in [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md), [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md), and [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md).

## Project Structure

- `app/`: FastAPI backend
- `app/api/routes/`: auth, CV, job, and match endpoints
- `app/core/`: settings, AI, security, validation, rate limiting
- `app/db/`: engine, sessions, schema bootstrap, CRUD helpers
- `app/models/`: SQLModel entities
- `app/schemas/`: API request/response models
- `app/services/`: PDF extraction, job analysis, CV matching, cover letters
- `frontend/`: React application
- `docs/`: project documentation

## Documentation

- [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md)
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)

## Notes

Local development can use SQLite if `DATABASE_URL` is omitted and `APP_ENV=development`. Production requires PostgreSQL.

