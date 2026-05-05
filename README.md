# JOBPI

**JOBPI** is a production-grade AI-powered job application assistant that centralizes and optimizes the job search process. The platform helps users analyze job postings, organize and manage CV libraries, evaluate fit between profiles and positions, generate tailored cover letters, and track application progress—all in a single, unified workflow.

**Status**: Version 1.0 live and operational on Vercel.

## Overview

The system is architected as a full-stack application with a FastAPI modular backend and a React SPA frontend, both deployed to Vercel. Authentication and file storage are handled by Supabase (Auth + Storage). AI analysis workflows use DSPy with OpenRouter or OpenAI-compatible providers, backed by structured output schemas, quality gates, and response normalization to ensure consistency and reliability.

## Core Features

**User & Auth**
- Secure registration, login, password reset, and session management via Supabase Auth.
- Email-based user lookup with automatic account linking for legacy users.
- Per-user RLS (Row-Level Security) policies at the database layer for data isolation.

**CV Library**
- Single and batch PDF upload with secure storage in Supabase Storage buckets.
- Signed download links for persistent access without exposing storage URLs.
- CV tagging, favorites, bulk operations (delete, tag), and flexible filtering.
- Per-CV detail views with summaries and match history.

**Job Analysis**
- Structured AI analysis with explicit field validation (seniority, role type, required/nice-to-have skills, responsibilities, interview tips, resume improvements, project ideas, learning paths).
- Intelligent fallback mode when AI analysis fails (pattern-based skill extraction, heuristic role detection).
- Job caching by context fingerprint to avoid redundant AI calls.
- Soft-delete support with recovery options.
- Job status tracking (saved, applied, interviewing, rejected, offer, archived) with applied-date recording.

**Matching & Comparison**
- CV-to-job fit scoring with actionable gap analysis.
- CV-to-CV comparison for a single job position (helps select which resume to use).
- Weighted compatibility scoring based on skill overlap, seniority fit, and role type alignment.

**LinkedIn Optimizer**
- AI-driven profile audit to align LinkedIn sections with specific roles and CVs.
- Tailored cold outreach message generation for connection requests, follow-ups, and referrals.

**Cover Letter Generation**
- AI-generated tailored cover letters using CV + job context.
- Language support (English & Spanish) with matching AI output.
- Rate-limited to prevent abuse; regeneration supported.

**Interview Preparation**
- Interview Simulator sessions per job and CV (`mixed`, `behavioral`, `technical`).
- STAR framework guidance generated per question, with category-aware hints (leadership, technical, failure/challenge).
- Session history by job, manual session loading, and markdown export for offline practice.
- Localized coaching copy in English and Spanish.

**Application Tracker**
- Unified view of all jobs with status, applied date, and notes.
- Match list showing CV-job pairs with compatibility scores.
- Soft-delete and recovery for deleted records.

**Multilingual Support**
- Full English and Spanish UI with matching AI response language.
- Localized error messages and helper text.

## Tech Stack

**Backend**
- **Framework**: FastAPI with Pydantic V2 for validation and serialization.
- **ORM & Schema**: SQLModel for type-safe database models; Alembic for migrations.
- **Database**: PostgreSQL in production, SQLite fallback for development.
- **Auth**: Supabase Auth (JWT-based sessions) with legacy JWT bridge for backward compatibility.
- **Storage**: Supabase Storage (private PDF buckets) with signed download URL generation.

**AI & Quality**
- **Framework**: DSPy for structured AI workflows.
- **Providers**: OpenRouter with fallback to Groq and OpenAI-compatible endpoints.
- **Resilience**: Circuit breaker pattern, request-level timeouts, token clamping, and automatic retries.
- **Output Quality**: Structured Pydantic schemas, response normalization (punctuation cleanup, parenthesis balancing, truncation handling), deduplication, and fallback analysis for AI failures.

**Frontend**
- **Framework**: React 18 with TypeScript and Vite for fast dev server + production builds.
- **Routing**: React Router for navigation and lazy-loaded pages.
- **Styling**: Tailwind CSS v4 with modern design token architecture.
- **Animations**: Framer Motion for entrance animations and micro-interactions.
- **API Integration**: Supabase JS client with async token retrieval; native Fetch API.
- **State Management**: React Context API for auth state and session management.
- **Interview UX**: Session setup, STAR answer drafting, markdown export, and category-aware interview guidance.

**Infrastructure & DevOps**
- **Deployment**: Vercel (both frontend and backend via serverless functions).
- **Rate Limiting**: Redis (optional) for distributed rate limiting; in-memory fallback for development.
- **Error Tracking**: Sentry (optional) for production error aggregation and alerting.
- **Observability**: Structured JSON logging with trace IDs for request correlation.

## Quality Commitment

JOBPI prioritizes **output consistency and reliability** over speed. The system:
- Uses **strict typed schemas** for all AI outputs to guarantee consistency.
- Implements **intelligent text normalization** to remove truncation artifacts, dangling abbreviations, and unbalanced punctuation.
- Employs **deduplication** logic to eliminate redundant items across recommendation lists.
- Includes **quality gates** (context fingerprints, fallback detection, meaningful-content validation) to avoid storing incomplete or formulaic results.
- Provides **graceful degradation**: when AI fails, the system serves pattern-based fallback analysis rather than errors or stale data.

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
6. Use Interview Simulator to start a prep session, draft STAR responses, and export your prep notes.
7. Review the Matches and Tracker views to monitor fit and application status across saved jobs.

## Notes

- The backend entrypoint for Vercel is `api/index.py`.
- The project keeps a legacy JWT bridge so older sessions can still be resolved during the migration to Supabase Auth.
- For deeper design notes and endpoint details, see the architecture and API docs in the `docs/` folder.

