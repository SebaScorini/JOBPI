# PROJECT CONTEXT

## What the Project Does

JOBPI is an AI-assisted job application workspace. It helps a user upload CVs, analyze job descriptions, compare CVs against a role, generate cover letters, and track the status of applications over time.

The product is designed to reduce manual tailoring work and make role matching more consistent through structured analysis and reusable CV data.

## Architecture Overview

- Frontend: React SPA for job analysis, CV management, matching, and tracking.
- Backend: FastAPI service that handles auth, persistence, request validation, and AI orchestration.
- Database: SQLModel over SQLite locally and PostgreSQL in production, typically via Supabase.
- AI: DSPy calling OpenRouter-backed models for job analysis, CV fit analysis, CV summaries, and cover letters.

## Backend Role

- Exposes authenticated REST endpoints under `/auth`, `/cvs`, `/jobs`, and `/matches`.
- Enforces request size limits and in-memory rate limits.
- Persists users, CVs, job analyses, and matches.
- Runs PDF extraction, preprocessing, and AI generation services.

## Frontend Role

- Serves the user-facing app shell, navigation, and routed screens.
- Calls the backend through `frontend/src/services/api.ts`.
- Stores the auth token in browser storage and attaches it to protected requests.
- Uses `VITE_API_URL` for the backend base URL and `VITE_SITE_URL` for canonical page metadata.

## Database Role

- Stores user-scoped data in `users`, `cvs`, `job_analyses`, and `cv_job_matches`.
- Keeps analysis payloads and CV-match data in JSON columns where appropriate.
- Uses runtime schema bootstrap, with SQLite compatibility handling for legacy local databases.

## Auth Flow

1. User registers or logs in through `/auth/register` or `/auth/login`.
2. Login returns a bearer token signed with `SECRET_KEY`.
3. The frontend stores the token and sends it as `Authorization: Bearer ...`.
4. Protected routes resolve the current user through the JWT subject.
5. All user-owned reads and writes are filtered by `user_id`.

## External Services

- Supabase PostgreSQL for production data.
- OpenRouter for AI model access through DSPy.
- Vercel for deployment of both backend and frontend.

## Related Docs

- [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md)
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)
- `COVER_LETTER_RATE_LIMIT_WINDOW_SECONDS`: cover-letter rate-limit window
- `COVER_LETTER_RATE_LIMIT`: cover-letter cap
- `CV_UPLOAD_RATE_LIMIT_WINDOW_SECONDS`: CV upload rate-limit window
- `CV_UPLOAD_RATE_LIMIT`: CV upload cap
- `MAX_PDF_SIZE_MB`: max single-PDF upload size
- `MAX_CVS_PER_UPLOAD`: max files for batch upload
- `MAX_JOB_DESCRIPTION_CHARS`: max job-description size
- `MAX_CV_TEXT_CHARS`: max cleaned CV text used downstream
- `SQLITE_TIMEOUT_SECONDS`: SQLite connection timeout
- `TRUSTED_USER_EMAIL`: exempt user for some limits/rate caps
- `CORS_ORIGINS`: comma-separated allowed frontend origins
- `CORS_MAX_AGE_SECONDS`: preflight cache max age
- Frontend:
- `VITE_API_URL`: backend base URL for the React app
- Notable behavior:
- If `VITE_API_URL` is missing in dev, frontend falls back to `http://localhost:8000`

## 11. External Services
- OpenRouter: primary LLM gateway for DSPy-driven features
- Supabase/PostgreSQL: intended production database target via `DATABASE_URL`
- SQLite: local development fallback database
- No OAuth provider, email service, queue, or object-storage integration is present in the current codebase

## 12. Deployment
- Docker:
- No `Dockerfile`, Compose file, or container orchestration config exists in the repository
- Vercel:
- No Vercel config present; frontend is a standard Vite app and could be deployed separately, but there is no repo-native setup
- Railway:
- No Railway config present
- Local run:
1. Create/activate Python virtual environment
2. Install `requirements.txt`
3. Run `uvicorn app.main:app --reload`
4. In `frontend/`, run `npm install` then `npm run dev`
5. Optional helper: `iniciar.bat` starts backend and frontend in separate Windows terminals
- Backend startup automatically creates/patches schema through app lifespan hook

## 13. How the System Works (Flow)
1. User signs in or registers from the React frontend.
2. Frontend stores JWT in localStorage and uses it on authenticated API calls.
3. User uploads CV PDFs or pastes a job description.
4. Backend route validates auth, request size, and rate limits.
5. For CV upload:
- PDF text is extracted and cleaned
- Duplicate CVs are detected by cleaned text
- A short library summary is generated and persisted
6. For job analysis:
- Job description is cleaned and compacted
- DSPy/OpenRouter generates structured analysis
- Result is cached and stored in `job_analyses`
7. For CV matching:
- Selected CV clean text and job clean description are passed to the CV analyzer
- Match record is created or refreshed in `cv_job_matches`
- Response includes fit summary, strengths, gaps, suggestions, and heuristic score
8. For CV comparison:
- Two individual match analyses are produced or reused
- Service chooses a winner based on heuristic score, fit level, gaps, and tie-breakers
9. For cover letters:
- Selected job + CV are sent to the cover-letter generator
- Output is normalized and cached on the job record
10. Tracker UI updates job status/notes, which are persisted directly on the job entity
11. Frontend renders normalized DTOs on dashboard, job details, library, matches, and tracker screens

## 14. Key Design Decisions
- Single-user-scoped domain model: every business entity is tied to `user_id`, making isolation explicit and simple.
- AI outputs are persisted, not recomputed on every request, reducing cost and latency.
- The job-analysis payload is stored as JSON instead of fully normalized tables, which keeps AI iteration flexible.
- Services own orchestration and fallback logic, while routes stay thin.
- SQLite compatibility is maintained for local development even though PostgreSQL is the intended production target.
- Runtime schema patching is used instead of formal migrations, likely to keep local iteration friction low.
- Frontend uses a single typed API adapter that maps backend DTOs into UI-friendly types.
- Language handling is split between UI language and AI response language, but both are coordinated from one context.

## 15. Known Limitations
- No formal migration system; schema evolution is handled manually at runtime.
- No automated test suite or repo-local test directory was found.
- Rate limiting is process-local memory only and will not behave consistently across multiple instances.
- JWT implementation is custom rather than using a hardened auth library.
- Match history and matches UI expose IDs more than rich domain labels, suggesting UX is still evolving.
- AI dependency is optional in code but core features degrade when OpenRouter is unavailable.
- Several frontend files contain encoding/mojibake artifacts in strings and comments, indicating text-encoding cleanup is still needed.
- No background jobs, queue, retry worker, or async persistence exists for long AI operations.
- No container/deployment manifests are included.

## 16. How to Extend This Project
- Add new backend features by following the existing pattern:
- define request/response schemas in `app/schemas`
- add or extend entities in `app/models`
- implement persistence helpers in `app/db/crud.py`
- keep orchestration in `app/services`
- expose routes in `app/api/routes`
- For new AI workflows, create a dedicated DSPy signature/module in `app/services`, normalize outputs aggressively, and add fallbacks or cache reuse.
- If data shape becomes more complex, introduce real migrations before expanding schema changes further.
- If deploying beyond a single process, replace in-memory rate limiting and caches with shared infrastructure.
- Frontend additions should usually:
- add/extend types in `frontend/src/types`
- add a typed client method in `frontend/src/services/api.ts`
- create/update a page or component under `frontend/src/pages` or `frontend/src/components`
- wire translations through `frontend/src/i18n/translations.ts`
- For new user-facing domains, preserve the user-scoped access pattern in every CRUD function and route.

## 17. Quick Mental Model
- Think of JOBPI as a two-part system:
- a React dashboard for managing jobs and CVs
- a FastAPI service that stores user data and runs AI-assisted analysis
- The main persistent objects are users, CVs, analyzed jobs, and CV-job matches.
- The main intelligence lives in service modules that clean text, call DSPy/OpenRouter, cache results, and save reduced structured outputs.
- If you understand `jobs -> analyze`, `cvs -> upload`, and `jobs/{id} -> match/compare/cover-letter`, you understand most of the product.
