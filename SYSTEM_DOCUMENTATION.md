# JOBPI System Documentation

## Purpose

This document is the backend and AI-system source of truth for JOBPI as implemented in this repository. It describes the code that exists today, not the intended future state.

## 1. System Overview

JOBPI is an AI-assisted job application backend with authenticated, user-scoped workflows for:

- Registering and authenticating users
- Uploading and managing CVs
- Extracting and cleaning PDF resume text
- Generating compact CV library summaries
- Analyzing job descriptions into structured guidance
- Matching a CV against a job
- Comparing two CVs for a job
- Generating tailored cover letters
- Tracking saved/applied job states and notes

The backend uses FastAPI, SQLModel, and Alembic. AI generation is handled through DSPy configured against an OpenRouter-compatible chat completion endpoint.

## 2. Core User Flows

### CV upload

1. An authenticated user uploads one or more PDFs to `POST /cvs/upload` or `POST /cvs/batch-upload`.
2. The route validates rate limits, request size, file size, and PDF MIME type.
3. `CvLibraryService.upload_cv()` extracts PDF text, preprocesses it, deduplicates by normalized `clean_text`, and generates a CV library summary.
4. The CV record is persisted and returned as a `CVRead` payload.

### Job analysis

1. An authenticated user sends title, company, and description to `POST /jobs/analyze`.
2. The route validates size and rate limits.
3. `JobAnalyzerService.analyze()` cleans and prunes the job description, checks DB and in-memory caches, then runs a DSPy module through the shared AI execution wrapper.
4. The AI output is normalized into a stable `JobAnalysisPayload` and stored as a `JobAnalysis`.
5. If the provider fails or the output is low quality, the request returns an error rather than silently inventing an analysis. The repository does include heuristic builder helpers in `app/services/job_analyzer.py`, but the live path still depends on the AI result meeting validation checks.

### CV match and compare

1. An authenticated user requests `POST /jobs/{job_id}/match-cvs`.
2. `CvLibraryService.match_job_to_cv()` loads the job and CV, checks for an existing stored match, and regenerates only when needed or when `regenerate=true`.
3. `CvAnalyzerService` compares a pruned job excerpt and a pruned CV excerpt.
4. The result is persisted as a `CVJobMatch` and returned together with the richer AI analysis payload.
5. `POST /jobs/{job_id}/compare-cvs` ranks candidates deterministically, using heuristic overlap score as the primary tie-breaker and fit level as the next signal.

### Cover letter generation

1. An authenticated user requests `POST /jobs/{job_id}/cover-letter`.
2. `CoverLetterService.generate_cover_letter()` loads the job and chosen CV, then checks for a stored cached cover letter for that exact job/CV/language pair.
3. If the cached letter does not look generic, it is returned directly.
4. Otherwise the service builds pruned job and CV excerpts and generates a short plain-text cover letter through DSPy.
5. On failure, the request returns an error. The live path does not substitute a heuristic cover letter.

### CV library summaries

1. `CvLibrarySummaryService.generate()` builds a compact CV context from representative lines in the cleaned text.
2. DSPy caching is disabled for the summary call so batch uploads do not surface stale results.
3. If the AI call succeeds, the summary is normalized and stored.
4. When a CV row has no stored library summary, serialization falls back to `summary`, then the first non-empty cleaned line, then `display_name`.

## 3. Architecture

### High-level backend structure

```text
app/
├─ main.py                  FastAPI app creation, middleware, exception handling
├─ api/routes/              HTTP endpoints
├─ dependencies/            Dependency injection helpers
├─ core/                    Settings, AI runtime, logging, security, rate limiting
├─ db/                      Engine, sessions, migrations, CRUD layer
├─ models/                  SQLModel ORM entities
├─ schemas/                 Request/response models
└─ services/                Business logic and AI orchestration
```

### Separation of concerns

- Routes handle HTTP shape, endpoint-specific rate limits, and payload size guards.
- Services contain the application behavior and coordinate CRUD, AI calls, preprocessing, normalization, and persistence.
- Core modules own configuration, AI execution, circuit breaking, security, logging, and rate limiting.
- The DB layer owns engine/session creation, CRUD operations, and migration bootstrapping.

## 4. AI System

AI is used in four places:

1. `app/services/job_analyzer.py`
2. `app/services/cv_analyzer.py`
3. `app/services/cover_letter_service.py`
4. `app/services/cv_library_summary_service.py`

There is no retrieval pipeline, embedding store, vector database, reranker, or OCR system in the backend code.

`app/core/settings.py` configures a single shared DSPy LM with:

- `OPENROUTER_BASE_URL`
- `OPENROUTER_API_KEY`
- `DSPY_MODEL`
- a clamped temperature range
- a task-specific max token ceiling

Per-call token overrides use `dspy_lm_override()` rather than reconfiguring the global model for each request.

All major AI calls go through the shared AI execution wrapper in `app/core/ai.py` and the circuit breaker in `app/core/circuit_breaker.py`. That gives each call timeout enforcement, retry/backoff, observability logs, and provider/auth error classification.

Practical AI behavior in the current code:

- `JobAnalyzerService` uses a smaller retry excerpt when a second attempt is allowed.
- `CvAnalyzerService` validates output quality and rejects low-quality responses.
- `CoverLetterService` only reuses stored letters that do not look generic.
- `CvLibrarySummaryModule` disables DSPy cache for the summary request so batch uploads stay isolated.

## 5. Auth, Rate Limiting, and Runtime

- Supabase-backed auth is first-class in both the backend and frontend.
- The backend still accepts legacy JWT formats during the rollout window.
- If `REDIS_URL` is set, rate limiting uses Redis for shared counters.
- If Redis is missing or unavailable, the limiter falls back to the in-memory backend.
- Production defaults are stricter than local defaults.
- Local development can fall back to SQLite when `DATABASE_URL` is omitted.
- Startup runs Alembic migrations and stamps legacy databases to the baseline when needed.
- Vercel uses `api/index.py` as the Python backend entrypoint, with `vercel.json` rewrites routing traffic to the app.
- The frontend reads `VITE_API_URL` for backend requests and `VITE_SITE_URL` for canonical URLs and password-reset redirects, with browser-origin fallback when available.

## 6. Persistence Model

The main persistence layer lives in `app/models/entities.py` and `app/db/crud.py`.

Relevant entities include:

- user records
- CV records and extracted text
- job analysis records
- CV/job match records
- generated cover-letter fields stored on job analysis rows

`app/db/migration_runner.py` and the Alembic migrations keep schema changes synchronized with the runtime.

## 7. Current Constraints

- Scanned or image-only PDFs are not supported because the backend does not perform OCR.
- There is no async task queue; AI and extraction happen in request-time flows.
- Process-local caches are not shared across instances.
- AI output can still be low quality or unavailable; the system prefers explicit errors over fabricating unsupported content.
- Rate limiting degrades to in-memory behavior when Redis is unavailable, which weakens cross-instance consistency.
- Some heuristic helper functions exist in the codebase, but the primary live paths still rely on the AI output or on already stored data.

## 8. Extensibility Guide

To add a new AI feature safely:

1. Add a dedicated service in `app/services/`.
2. Keep the DSPy `Signature` small and evidence-based.
3. Reuse `run_ai_call_with_circuit_breaker()`.
4. Preserve response shapes and normalization rules.
5. Add route-level validation and rate limiting if the feature is exposed over HTTP.
6. Add tests for the happy path, failure path, and cache behavior if applicable.

When changing prompt semantics, update any related cache fingerprinting or versioning so stale cached data does not leak into the new behavior.

## 9. Summary

JOBPI’s backend architecture is intentionally narrow:

- FastAPI routes for transport
- a service layer for business logic
- CRUD for persistence
- DSPy-based AI modules behind a shared execution wrapper
- deterministic preprocessing and conservative validation to keep the product predictable

That structure keeps the system relatively easy to extend as long as new work follows the same pattern instead of bypassing it.