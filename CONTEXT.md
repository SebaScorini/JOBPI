# CONTEXT

## Project Overview

**JOBPI** is a production-grade AI job application assistant that centralizes the entire job search workflow. Users can upload and organize CVs, analyze job postings, evaluate fit, generate cover letters, and track applications—all with AI-powered insights and a focus on output quality and reliability.

**Current Status**: Version 1.0 live and operational.

## Value Proposition

- **CV Organization**: Upload multiple CVs, tag them, mark favorites, and manage in one place.
- **Deep Job Analysis**: AI-driven breakdown of roles (seniority, skills, responsibilities, interview prep, learning paths, portfolio ideas).
- **Smart Matching**: Compare CVs against jobs; identify skill gaps and compatibility scores.
- **Tailored Outreach**: Generate cover letters customized to both CV and job context.
- **Application Tracking**: Unified tracker for job statuses, dates applied, and personal notes.
- **Multi-Language**: Full English and Spanish support with matching AI output.

## Tech Stack Summary

**Backend Architecture**
- **Framework**: FastAPI with Pydantic V2 for type-safe request/response handling.
- **Data Layer**: SQLModel (TypeScript-inspired ORM) with Alembic migrations on PostgreSQL (production) or SQLite (dev).
- **Auth**: Supabase Auth (JWT sessions) + legacy JWT bridge for older users.
- **Storage**: Supabase Storage (private PDF buckets) with signed URL generation for downloads.

**AI & Quality Systems**
- **DSPy Framework**: Structured AI workflows with explicit Pydantic output schemas.
- **Model Providers**: OpenRouter (primary), Groq, OpenAI-compatible endpoints.
- **Resilience**: Circuit breaker, request-level timeouts, token clamping, automatic retries.
- **Output Quality**: Response normalization, deduplication, fallback analysis mode, context fingerprinting.

**Frontend Architecture**
- **Stack**: React 18 + TypeScript + Vite + React Router + Tailwind CSS + Framer Motion.
- **Auth State**: React Context with Supabase session management.
- **API Layer**: Fetch API with async token retrieval; Supabase JS client.

**Infrastructure**
- **Deployment**: Vercel (both frontend and backend serverless).
- **Rate Limiting**: Redis (distributed, optional) or in-memory (dev).
- **Observability**: JSON logging with trace IDs, Sentry for error aggregation (optional).

## Core Services

### Authentication & Authorization
- `app/dependencies/auth.py` - JWT verification, Supabase token validation, user resolution.
- `app/core/supabase_auth.py` - Token parsing, email-based user lookup, auto-linking for legacy users.
- **RLS Policies**: Row-level security at the database ensures users can only access their own jobs, CVs, and matches.

### CV Management
- `app/services/pdf_extractor.py` - PDF text extraction with fallback for scanned documents.
- `app/services/cv_library_service.py` - CV persistence, tagging, favorites, bulk operations, library summaries.
- `app/services/supabase_storage.py` - Secure PDF upload, signed download URL generation, storage cleanup.

### Job Analysis
- `app/services/job_preprocessing.py` - Job description cleaning, context building, token estimation, context fingerprinting.
- `app/services/job_analyzer.py` - AI analysis generation with structured output schema, fallback mode, caching, soft-delete.
  - **Structured Output**: Seniority, role type, required skills, nice-to-have skills, responsibilities, interview tips, resume tips, learning path, gaps, project ideas.
  - **Quality Gates**: Validates content completeness, detects formulaic outputs, filters cached results.
  - **Response Normalization**: Cleans punctuation, balances parentheses, removes truncation artifacts, deduplicates items.

### Matching & Comparison
- `app/services/cv_library_service.py` - CV-to-job fit scoring, gap analysis, CV comparison.
- Weighted scoring based on skill overlap, seniority alignment, role type match.

### Cover Letter Generation
- `app/services/cover_letter_service.py` - AI-generated tailored cover letters using CV + job context.
- Language-aware and rate-limited.

### AI & Quality
- `app/core/ai.py` - Timeout wrapper, circuit breaker, truncation detection, token clamping.
- `app/models/ai_schemas.py` - Pydantic models for all AI outputs.

### Data Persistence & Soft Deletes
- `app/db/crud.py` - All CRUD operations filter `deleted_at IS NULL` to support soft-delete recovery.
- Migrations in `app/db/migrations/` manage schema versioning (Alembic).

## AI Output Quality Strategy

The system prioritizes **consistency, reliability, and signal-heavy recommendations** over brevity:

1. **Strict Schemas**: All AI outputs adhere to explicit Pydantic models with field type validation.
2. **Response Normalization**: 
   - Removes unnecessary punctuation, balances parentheses.
   - Strips dangling abbreviations (e.g., "e.g." at truncation).
   - Cleans unmatched closing parentheses.
3. **Deduplication**: Prevents redundant recommendations across lists using semantic signatures.
4. **Quality Gates**: 
   - Rejects incomplete or formulaic responses based on heuristic detection.
   - Requires minimum content thresholds before caching.
5. **Fallback Mode**: If AI fails, the system provides pattern-based analysis (skill extraction, heuristic seniority/role detection) rather than errors.
6. **Context Fingerprints**: Caching by content hash avoids re-running identical analyses.

## Known Limitations

- AI output can be generic or repetitive if the provider returns weak content.
- PDF extraction fails on scanned/image-only PDFs (fallback is manual text entry).
- Cached results remain stale until user regenerates or input changes.
- Language limited to English and Spanish.
- Rate limiting is per-process (in-memory) by default; Redis required for distributed rate limiting.

## Database Schema

**Users** - Authentication + profile (supabase_user_id, email, name, created_at, updated_at, deleted_at).
**CVs** - Resume storage (user_id, title, content_text, storage_path, is_favorite, tags, created_at, updated_at, deleted_at).
**Jobs** - Job postings + analysis (user_id, title, company, description, clean_description, analysis_result, status, notes, is_saved, applied_date, created_at, updated_at, deleted_at).
**JobMatches** - CV-to-job fit (user_id, job_id, cv_id, match_score, gaps, created_at, updated_at, deleted_at).

## Deployment

- **Frontend**: Deployed to Vercel, served from CDN.
- **Backend**: Deployed to Vercel as serverless functions (`api/index.py`).
- **Database**: PostgreSQL hosted on Supabase.
- **Storage**: Supabase Storage buckets for PDFs.
- **Environment Config**: `.env` for local, `.config/.env.docker` for Docker, Vercel env vars for production.

## Development

- **Backend**: `uvicorn app.main:app --reload` (local) or `make up` (Docker).
- **Frontend**: `npm run dev` in `/frontend` (Vite dev server on localhost:5173).
- **Tests**: `pytest tests/` (backend) or `npm run test` (frontend).
- **Migrations**: `alembic upgrade head` or handled automatically on deployment.

## Service Map

- `app/main.py` - FastAPI app setup, CORS, request logging, error handling, health endpoint.
- `app/api/routes/auth.py` - `/auth/register`, `/auth/login`, `/auth/me`.
- `app/api/routes/cvs.py` - CV upload, batch upload, list, detail, download, tags, favorites, bulk actions.
- `app/api/routes/jobs.py` - Job analysis, list, detail, delete, status, notes, saved toggle, match, compare, cover letter.
- `app/api/routes/matches.py` - Match list and match detail.
- `app/services/pdf_extractor.py` - PDF text extraction and CV preprocessing.
- `app/services/job_preprocessing.py` - Job and CV excerpt building, noise removal, token estimation, context fingerprints.
- `app/services/job_analyzer.py` - Job analysis generation and persistence.
- `app/services/cv_library_service.py` - CV library persistence, summaries, matching, comparison, recommendation selection.
- `app/services/cv_analyzer.py` - CV-to-job fit analysis.
- `app/services/cv_library_summary_service.py` - Compact CV library summaries.
- `app/services/cover_letter_service.py` - Cover letter generation.
- `app/services/supabase_storage.py` - Signed download URLs and PDF storage operations.
- `app/core/ai.py` - AI timeout wrapper, circuit breaker, truncation detection, token clamping.
- `app/core/supabase_auth.py` and `app/dependencies/auth.py` - Token verification and current-user resolution.

## Token Strategy

- Job and CV text are compacted before AI calls so the model sees signal-heavy excerpts instead of raw documents.
- The code uses per-task budgets, not a single global cap, and retries can use smaller excerpts or lower token budgets.
- `dspy_lm_override` clamps max tokens and keeps reasoning disabled for deterministic output size control.
- Context fingerprints and in-memory caches avoid re-running identical analyses when the stored result is still valid.

## Known Output Problems

- AI output can still be generic, repetitive, or too short when the provider returns weak content.
- Summaries are intentionally compact and may be truncated by the configured token or character limits.
- Cached job and cover letter results can stay stale until the user regenerates them or the input changes.
- PDF extraction can fail on scanned or image-only PDFs.
- AI output language is limited to English or Spanish.

## AI Output Rules

- Use only evidence present in the uploaded CV, pasted job description, or persisted analysis.
- Do not invent experience, metrics, tools, seniority, or job requirements.
- Prefer concrete, role-specific language over generic career advice.
- Keep every output field in the requested language.
- Respect schema boundaries and length limits, and shorten rather than pad.
- If the evidence is weak, say so directly instead of compensating with filler.