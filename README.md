# JOBPI

JOBPI is an AI-powered job application assistant for analyzing roles, managing a CV library, matching resumes to jobs, generating cover letters, and tracking application progress.

## Overview

The backend is a FastAPI service with SQLModel persistence, Supabase Auth and Storage integration, and DSPy-powered AI workflows through OpenRouter or any OpenAI-compatible provider (including Groq). The frontend is a React + Vite SPA that provides the dashboard, job analysis, CV library, match views, and application tracker.

## Features

- Supabase-backed sign up, login, password reset, and session handling.
- Single and batch CV upload with PDF storage and signed download links.
- CV library management with search, tags, favorites, bulk delete, and bulk tagging.
- Job analysis with structured AI output, saved jobs, status updates, notes, and soft delete.
- CV-to-job match analysis, CV comparison, and tailored cover letter generation.
- Match list and tracker views for reviewing application progress.
- English and Spanish UI plus matching AI response language.

## Tech Stack

- Backend: FastAPI, SQLModel, Alembic, PostgreSQL, SQLite fallback for development.
- AI: DSPy, OpenRouter, token clamping, circuit breaker retries, and response normalization.
- Auth and storage: Supabase Auth, Supabase Storage, legacy JWT bridge support.
- Frontend: React 18, TypeScript, Vite, React Router, Tailwind CSS, Framer Motion, Supabase JS.
- Ops: Redis optional for shared rate limiting, Sentry optional for error tracking, Vercel deployment support.

## Setup

### 1. Prerequisites

- Python 3.12+
- Node.js 18+
- npm
- PostgreSQL if you want to run against a local database instead of the SQLite fallback
- An OpenRouter, Groq, or OpenAI-compatible API key
- A Supabase project if you want auth and storage to work end-to-end

### 2. Environment variables

The full list is documented in [.env.example](.env.example) and [.config/.env.docker](.config/.env.docker).

Backend variables you will usually need:

- `DATABASE_URL` - PostgreSQL in production, optional SQLite fallback in development.
- `SECRET_KEY`
- `OPENROUTER_API_KEY` (or `GROQ_API_KEY` / `OPENAI_API_KEY`)
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_JWT_SECRET`
- `SUPABASE_SERVICE_ROLE_KEY`
- `CORS_ORIGINS`
- `REDIS_URL` if you want distributed rate limiting

Frontend variables you will usually need:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`
- `VITE_API_URL` if the frontend is not talking to the default local backend or hosted API
- `VITE_SITE_URL` for canonical URLs and password reset redirects

### 3. Docker setup

Docker is the fastest way to run the whole stack locally.

```powershell
Copy-Item .config\.env.docker .env
make up
```

Then open:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs

Useful commands:

```bash
make logs
make down
make restart
```

### 4. Local backend + frontend

Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Run Locally

If you use the Docker stack, run `make up` from the repository root and wait for the backend health check to pass. If you run services separately, start the backend first and then the frontend so the Vite app can reach the API.

The backend can fall back to SQLite in development when `DATABASE_URL` is omitted, but production requires PostgreSQL.

## Basic Usage

1. Register or sign in on the landing page.
2. Open the CV library and upload one or more PDF resumes.
3. Go to Job Analysis, paste a job description, and generate a structured analysis.
4. Open the resulting job detail page to match a CV, compare two CVs, or generate a cover letter.
5. Update the job status, save notes, or toggle the saved flag as your application progresses.
6. Review the Matches and Tracker views to monitor fit and application status across saved jobs.

## Notes

- The backend entrypoint for Vercel is `api/index.py`.
- The project keeps a legacy JWT bridge so older sessions can still be resolved during the migration to Supabase Auth.
- For deeper design notes and endpoint details, see the architecture and API docs in the `docs/` folder.

