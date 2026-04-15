# JOBPI

AI-powered job application assistant for CV optimization, role matching, and application tracking.

# JOBPI

AI-powered job application assistant for CV optimization, role matching, and application tracking.

## Overview

JOBPI helps users analyze job descriptions, manage a personal CV library, compare CVs against a role, generate cover letters, and track applications in one workflow. The backend handles authentication, persistence, and AI-assisted analysis; the frontend provides the dashboard and job-management experience.

## Tech Stack

Backend: FastAPI, SQLModel, PostgreSQL on Supabase, Supabase Auth & Storage, SQLite fallback for local development, DSPy, OpenRouter.

Frontend: React, TypeScript, Vite, Tailwind CSS, Framer Motion, React Router.

## Features

- Supabase Authentication (JWT-based)
- Single and batch CV upload with Supabase Storage
- CV summaries, tags, and favorite CV support
- Job description analysis with modern motion UI
- CV-to-job matching and comparison
- Tailored cover letter generation
- Job tracking with soft-delete and audit support
- Job-detail copy actions for high-signal analysis sections

```bash
# Copy environment template
cp .config/.env.docker .env

# Customize environment variables in .env as needed

# Start all services (backend, frontend, database)
make up

# View logs
make logs

# Access the app
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# Docs: http://localhost:8000/docs
```

See [DOCKER_QUICKSTART.md](docs/DOCKER_QUICKSTART.md) for detailed Docker setup.

### Option 2: Local Installation

If you want to use your own `OPENROUTER_API_KEY` and `DSPY_MODEL`:

**Backend:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

### Option 3: Deployed Version

Use the hosted version at https://jobpi-app.vercel.app/

## Deployment

The backend is deployed on Vercel through the Python entrypoint in `api/index.py`. Production should use Supabase PostgreSQL via `DATABASE_URL`, `APP_ENV=production`, a strong `SECRET_KEY`, and a valid `OPENROUTER_API_KEY`.

For production observability and scaling, also set:

- `SENTRY_DSN` for runtime error tracking
- `REDIS_URL` for shared rate limiting across instances

The frontend should be built with `VITE_API_URL` pointing to the deployed backend. `VITE_SITE_URL` is recommended for production canonical URLs.
The committed frontend runtime currently requires `VITE_API_URL`; `VITE_SITE_URL` remains optional deployment metadata.

If you use the hosted version, open https://jobpi-app.vercel.app/ and sign in normally. If you install locally, you can point the app to your own backend and configure your own AI provider values in `.env`.

See the detailed guides in [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md), [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md), and [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md).

## Project Structure

JOBPI is organized for clarity and maintainability:

```text
JOBPI/
|-- .config/    Configuration and Docker resources
|-- .scripts/   Helper scripts
|-- api/        Vercel backend entrypoint
|-- app/        Backend FastAPI application
|-- frontend/   React application
|-- docs/       Canonical documentation
|-- tests/      Test suite
```

For a complete directory guide, see [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md).

### Backend Architecture

- `app/api/routes/`: auth, CV, job, and match endpoints
- `app/core/`: settings, AI, security, validation, rate limiting
- `app/db/`: database engine, sessions, schema, CRUD operations
- `app/models/`: SQLModel ORM entities
- `app/schemas/`: Pydantic request/response validation
- `app/services/`: PDF extraction, job analysis, CV matching, cover letters

### Frontend Structure

- `frontend/src/pages/`: page-level components
- `frontend/src/components/`: reusable components
- `frontend/src/services/`: API client
- `frontend/src/context/`: React context state
- `frontend/src/i18n/`: internationalization files

## Testing

Tests are organized in the `tests/` directory and cover validation, auth, uploads, pagination, matching, cover-letter generation, and API reliability flows. The backend pytest suite imports the application directly and does not require a separately running API server.

### Backend tests
```bash
pytest -q
pytest --cov=app --cov-report=term-missing -q
```

### Local benchmark baseline
```bash
python tests/benchmark.py
```

### Frontend tests
```bash
cd frontend
npm run test
npm run build
```

### CI
The repository includes [ci.yml](.github/workflows/ci.yml) to run backend tests with coverage, a benchmark smoke script, frontend tests, and the frontend production build.

See [tests/README.md](tests/README.md) for more detailed test documentation.

### Sprint 7 verification
```bash
pytest -q
pytest --cov=app --cov-report=term-missing -q
python tests/benchmark.py
cd frontend
npm run test
npm run build
```

## Documentation

### Getting Started
- [DOCKER_QUICKSTART.md](docs/DOCKER_QUICKSTART.md) - 5-minute Docker setup
- [PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) - Full directory guide

### Reference & Architecture
- [PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md) - Project overview
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design
- [API_REFERENCE.md](docs/API_REFERENCE.md) - REST API endpoints

### Configuration & Deployment
- [ENVIRONMENT.md](docs/ENVIRONMENT.md) - All environment variables
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Production deployment
- [RATE_LIMITING.md](docs/RATE_LIMITING.md) - Runtime limiter behavior and Redis fallback
- [HEALTH_CHECK.md](docs/HEALTH_CHECK.md) - Post-deploy validation checklist
- [DOCKER.md](docs/DOCKER.md) - Complete Docker guide with 40+ commands

## Notes

Local development can use SQLite if `DATABASE_URL` is omitted and `APP_ENV=development`. Production requires PostgreSQL.

