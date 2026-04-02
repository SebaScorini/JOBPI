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

### Option 1: Docker (Recommended)

The easiest way to run the full stack with PostgreSQL:

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

The frontend should be built with `VITE_API_URL` pointing to the deployed backend. `VITE_SITE_URL` is recommended for production canonical URLs.

If you use the hosted version, open https://jobpi-app.vercel.app/ and sign in normally. If you install locally, you can point the app to your own backend and configure your own AI provider values in `.env`.

See the detailed guides in [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md), [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md), and [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md).

## Project Structure

JOBPI is organized for clarity and maintainability:

```
├── .config/              # Configuration and Docker resources
│   └── docker/          # Docker compose, images, nginx config
├── .scripts/            # Helper scripts
├── app/                 # Backend FastAPI application
├── frontend/            # Frontend React application
├── docs/                # Documentation
└── tests/               # Test suite
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

Tests are organized in the `tests/` directory and cover validation, pagination, and API health.

### Run tests with Docker
```bash
make test
```

### Run tests locally
```bash
python tests/test_improvements.py
```

### Run with pytest
```bash
pytest                          # Run all tests
pytest tests/test_improvements.py -v  # Specific test
pytest --cov=app tests/         # With coverage
```

See [tests/README.md](tests/README.md) for detailed test documentation.

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
- [DOCKER.md](docs/DOCKER.md) - Complete Docker guide with 40+ commands

## Notes

Local development can use SQLite if `DATABASE_URL` is omitted and `APP_ENV=development`. Production requires PostgreSQL.

