# PROJECT CONTEXT

JOBPI is an authenticated AI job application assistant. It helps users analyze job descriptions, organize CVs, compare fit across resumes, generate cover letters, and track application progress. The backend is a FastAPI modular monolith and the frontend is a React SPA.

## Tech Stack

- Backend: FastAPI, SQLModel, Alembic, PostgreSQL in production, SQLite fallback in development.
- Auth and storage: Supabase Auth, Supabase Storage, legacy JWT bridge support for older sessions.
- AI: DSPy with OpenRouter models, circuit breaker retries, token clamping, and request-level timeouts.
- Frontend: React 18, TypeScript, Vite, React Router, Tailwind CSS, Framer Motion, Supabase JS.
- Infra: Redis optional for distributed rate limiting, Sentry optional for error tracking, Vercel deployment support.

## Core Features

- User registration, login, profile lookup, logout, password reset, and session recovery through Supabase.
- Single and batch PDF CV upload with Supabase Storage-backed downloads.
- CV tagging, favorites, bulk delete, bulk tag, list filtering, and per-CV detail views.
- Job posting analysis with structured AI output, saved state, notes, and application status tracking.
- CV-to-job matching, CV comparison for a job, and AI-generated cover letters.
- Match listing and tracker views for application progress.
- English and Spanish UI plus matching AI response language.

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

## Next References

- Runtime architecture and flows: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- API contract details: [`docs/API_REFERENCE.md`](API_REFERENCE.md)
- Deployment and operations: [`docs/DEPLOYMENT.md`](DEPLOYMENT.md)
- Full environment variable reference: [`docs/ENVIRONMENT.md`](ENVIRONMENT.md)