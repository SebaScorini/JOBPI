# PROJECT CONTEXT

**JOBPI** is a production-grade AI-powered job application assistant that centralizes CV management, job analysis, CV-to-job matching, cover letter generation, and application tracking in a unified workflow.

**Status**: Version 1.0 operational on Vercel.

## What the Project Does

- **CV Library**: Upload, organize, tag, and manage multiple PDF resumes with secure cloud storage.
- **Job Analysis**: AI-driven structured analysis of job postings (seniority, skills, responsibilities, interview prep, resume tips, project ideas).
- **Smart Matching**: Compare CVs to jobs, identify skill gaps, and score compatibility.
- **LinkedIn Optimizer**: AI-driven profile audit and tailored networking message generator.
- **Interview Prep**: Dedicated simulator with STAR technique guidance and session tracking.
- **Cover Letters**: Generate tailored cover letters using CV + job context with language matching.
- **Application Tracking**: Unified tracker for job statuses, applied dates, and personal notes.
- **Multilingual**: Full English and Spanish support with AI output in matching language.

## Architecture

### Frontend
- **Location**: `frontend/`
- **Tech**: React 18 + TypeScript + Vite + Tailwind CSS + Framer Motion
- **Routing**: React Router with lazy-loaded pages
- **State**: React Context for auth state, Supabase JS client for session management
- **API Client**: Single `frontend/src/services/api.ts` with async token retrieval
- **Deployment**: Vercel CDN

### Backend
- **Location**: `app/`
- **Tech**: FastAPI + SQLModel + Alembic + PostgreSQL
- **Architecture**: Modular services (job_analyzer, cv_library_service, cover_letter_service, etc.)
- **Auth**: Supabase Auth (JWT sessions) with legacy JWT bridge
- **Storage**: Supabase Storage (private PDF buckets) with signed URLs
- **AI**: DSPy workflows with structured Pydantic output schemas (Job Analysis, Match, Cover Letter, LinkedIn, Interviews)
- **Quality**: Response normalization, deduplication, fallback mode, context fingerprinting, circuit breaker retries
- **Testing**: Playwright "Critical Path" E2E suite for core workflows
- **Deployment**: Vercel serverless functions (`api/index.py` entrypoint)

### Data Layer
- **Production DB**: PostgreSQL on Supabase
- **Development DB**: SQLite with automatic Alembic migration fallback
- **Schema**: Users, CVs, Jobs, JobMatches with soft-delete support (`deleted_at` field)
- **RLS**: Row-level security policies ensure user data isolation at DB level
- **Migrations**: Alembic versioning in `app/db/migrations/`

### External Services
- **Auth & Storage**: Supabase (Auth, Storage, PostgreSQL)
- **AI Models**: OpenRouter (primary), Groq, or OpenAI-compatible endpoints
- **Error Tracking**: Sentry (optional) for production errors
- **Rate Limiting**: Redis (distributed, optional) or in-memory (development)
- **Deployment**: Vercel (both frontend and backend)

## Core Request Flow

1. **Authentication**: User registers/logs in via Supabase Auth → frontend stores session.
2. **Protected Requests**: Frontend sends bearer token on all protected API calls.
3. **Backend Validation**: Auth middleware resolves current user from JWT → enforces ownership checks.
4. **Service Orchestration**: Routes delegate to services (job_analyzer, cv_library_service, etc.).
5. **AI Workflows**: DSPy modules run structured analysis with timeouts, circuit breakers, and quality gates.
6. **Response Normalization**: AI output is validated, deduplicated, and cleaned before persistence/return.
7. **Persistence**: Results stored in PostgreSQL with soft-delete support and RLS policies.

## Key Quality Principles

- **Structured AI Output**: All AI responses validate against strict Pydantic schemas.
- **Response Normalization**: Automatic cleanup of truncation artifacts, punctuation, and dangling content.
- **Deduplication**: Semantic deduplication prevents redundant recommendations across lists.
- **Quality Gates**: Validates completeness and rejects formulaic/incomplete results.
- **Graceful Fallback**: When AI fails, the system provides pattern-based analysis instead of errors.
- **Caching by Fingerprint**: Context-aware caching avoids redundant AI calls for identical inputs.

## Development Setup

**Backend**:
```bash
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**:
```bash
cd frontend
npm install
npm run dev
```

**Docker** (full stack):
```bash
make up
# http://localhost:3000 (frontend)
# http://localhost:8000 (backend)
```

## Environment Variables

**Backend Essential**:
- `DATABASE_URL` - PostgreSQL connection
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`, `SUPABASE_SERVICE_ROLE_KEY`
- `OPENROUTER_API_KEY` (or `GROQ_API_KEY`, `OPENAI_API_KEY`)
- `CORS_ORIGINS` - for frontend origin allowlist

**Frontend Essential**:
- `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- `VITE_API_URL` (optional; defaults to backend at localhost:8000 in dev)

Full list: `.env.example` (backend) and `frontend/.env` (frontend).

## Canonical Docs

- [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) - Detailed project overview
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - System architecture and data flow
- [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) - REST API endpoints
- [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) - Environment setup guide
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)
- [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)
