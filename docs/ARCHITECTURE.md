# ARCHITECTURE

JOBPI is a modular monolith with a React SPA on the client, a FastAPI backend on the server, and Supabase-backed identity and storage. The system is optimized around short, structured AI calls rather than long free-form generation.

## System Design

| Layer | Main Responsibility |
| --- | --- |
| `frontend/` | React SPA, auth/session handling, routing, page transitions, and API calls. |
| `app/main.py` | FastAPI application setup, CORS, request logging, error shaping, health check. |
| `app/api/routes/` | HTTP endpoints for auth, CVs, jobs, and matches. |
| `app/services/` | PDF extraction, preprocessing, job analysis, CV analysis, summaries, matches, cover letters, storage integration. |
| `app/db/` | SQLModel CRUD, session handling, and migrations. |
| `app/core/` | Settings, AI execution, rate limiting, auth verification, logging, runtime setup. |
| Supabase | Auth, storage, and production database support. |
| OpenRouter + DSPy | LLM execution for job analysis, CV fit analysis, summaries, and cover letters. |

The Vercel backend entrypoint is `api/index.py`, which re-exports the FastAPI app defined in `app.main`.

## Main Components

### Backend

- `app/api/routes/auth.py` exposes `/auth/register`, `/auth/login`, and `/auth/me`.
- `app/api/routes/cvs.py` exposes upload, batch upload, list, detail, download, tag, favorite, bulk delete, and bulk tag flows.
- `app/api/routes/jobs.py` exposes job analysis, list, detail, delete, status updates, notes, saved toggles, match generation, compare flows, and cover letter generation.
- `app/api/routes/matches.py` exposes match listing and match detail.
- `app/models/entities.py` contains the SQLModel tables for users, CVs, job analyses, and CV-job matches.
- `app/db/crud.py` owns persistence logic, soft deletes, deduplication helpers, and storage cleanup.

### Frontend

- `frontend/src/App.tsx` defines the route tree and lazy-loaded screens.
- `frontend/src/context/AuthContext.tsx` wraps Supabase sessions and resolves the backend user profile.
- `frontend/src/context/LanguageContext.tsx` provides UI i18n and maps the UI language to the AI response language.
- `frontend/src/context/AppThemeContext.tsx` manages light, dark, and system theme state.
- `frontend/src/pages/` contains the dashboard, CV library, job analysis, job detail, matches, tracker, and auth screens.
- `frontend/src/services/api.ts` is the typed API client for all backend endpoints.

### AI Services

- `app/services/job_analyzer.py` analyzes job descriptions into structured fields such as summary, skills, responsibilities, prep, learning path, and interview guidance.
- `app/services/cv_analyzer.py` compares a CV against a job description and returns fit summary, strengths, missing skills, improvements, rewritten bullets, interview focus, and next steps.
- `app/services/cv_library_summary_service.py` creates compact library summaries for CV cards.
- `app/services/cover_letter_service.py` generates a concise cover letter grounded in the selected job and CV.
- `app/services/job_preprocessing.py` builds signal-heavy excerpts and fingerprints so analyses can be cached and retried deterministically.

## HTTP Surface

### Auth

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

### CVs

- `POST /cvs/upload`
- `POST /cvs/batch-upload`
- `GET /cvs`
- `GET /cvs/{cv_id}`
- `GET /cvs/{cv_id}/download`
- `PATCH /cvs/{cv_id}/tags`
- `PATCH /cvs/{cv_id}/toggle-favorite`
- `POST /cvs/bulk-delete`
- `POST /cvs/bulk-tag`
- `DELETE /cvs/{cv_id}`

### Jobs

- `POST /jobs/analyze`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `DELETE /jobs/{job_id}`
- `PATCH /jobs/{job_id}/status`
- `PATCH /jobs/{job_id}/notes`
- `PATCH /jobs/{job_id}/toggle-saved`
- `POST /jobs/{job_id}/match-cvs`
- `POST /jobs/{job_id}/compare-cvs`
- `POST /jobs/{job_id}/cover-letter`

### Matches

- `GET /matches`
- `GET /matches/{match_id}`

### Health

- `GET /health`

## Data Flow

### CV Upload Flow

1. The frontend sends a PDF through `/cvs/upload` or `/cvs/batch-upload`.
2. The backend validates authentication, content type, request size, and per-user rate limits.
3. `pdf_extractor.py` extracts raw text and `job_preprocessing.py` removes noise and keeps high-signal sections.
4. `cv_library_service.py` deduplicates by cleaned text, generates or refreshes a library summary, stores the PDF in Supabase Storage, and persists the CV row.
5. The API returns the stored CV metadata for the UI.

### Job Analysis Flow

1. The frontend submits title, company, description, and UI language to `/jobs/analyze`.
2. `job_preprocessing.py` cleans the description, prioritizes useful sections, and truncates to the target size.
3. `job_analyzer.py` runs a DSPy module with a token budget and a retry budget through the AI circuit breaker.
4. The analysis is normalized into `JobAnalysisPayload`, stored, cached, and returned to the frontend.

### Match, Compare, and Cover Letter Flow

1. The job detail page requests CV matching, CV comparison, or cover-letter generation.
2. `cv_library_service.py` loads the job and selected CVs, reuses valid cached results where possible, and computes a heuristic score for match ordering.
3. `cv_analyzer.py` produces the structured fit analysis used by match and comparison views.
4. `cover_letter_service.py` generates a short cover letter, normalizes it, and persists the result on the job row.

## Service Interactions

- `get_current_user` accepts Supabase JWTs and, during the migration window, legacy app JWTs.
- `enforce_rate_limit` uses Redis when `REDIS_URL` is configured and falls back to in-memory counters otherwise.
- `run_ai_call_with_circuit_breaker` wraps every AI request with timeouts, retries, token-budget control, and truncation detection.
- `configure_runtime_environment` sets `DSPY_CACHEDIR` on Vercel so the runtime uses a writable temporary path.
- `SupabaseStorageService` creates signed URLs for downloads and removes PDFs when CVs are deleted.

## AI Design Choices

- `job_preprocessing.py` strips low-signal content, keeps requirements and responsibilities, and extracts CV lines that are more likely to matter to the model.
- `estimate_payload_tokens` and the context fingerprint helpers reduce unnecessary repeated work.
- `dspy_lm_override` clamps max tokens and disables reasoning output to keep responses concise.
- `CvLibrarySummaryService` uses a fresh DSPy instance for per-upload isolation so batch uploads do not leak stale summary state.
- `cv_library_service.py` rejects fallback-like analyses and re-runs or falls back to cached data only when the stored output still looks trustworthy.

## Key Decisions and Trade-offs

- SQLite exists only as a development fallback. Production expects PostgreSQL.
- CVs, jobs, and matches use soft deletes so application history is preserved and dependent records can be cleaned up safely.
- AI outputs are intentionally bounded and normalized, which reduces noise but can also shorten responses when the model is verbose or underperforms.
- The comparison endpoint returns decision-oriented fields only, which keeps the UI focused and avoids duplicating the full match payload.
- The frontend uses route-level lazy loading and suspense fallbacks so the app stays responsive while loading feature-heavy screens.

## Current Limitations

- AI output can still become generic or repetitive when the provider response is weak.
- Short summaries are a deliberate product choice, so some detail is sacrificed for speed and consistency.
- Scanned PDFs or CVs with little extractable text can fail early in preprocessing.
- English and Spanish are the only supported output languages.

## Related Docs

- Context and boundaries: [`docs/PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md)
- API contract: [`docs/API_REFERENCE.md`](API_REFERENCE.md)
- Deployment runbook: [`docs/DEPLOYMENT.md`](DEPLOYMENT.md)
- Env reference: [`docs/ENVIRONMENT.md`](ENVIRONMENT.md)