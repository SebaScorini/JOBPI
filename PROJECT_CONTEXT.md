# PROJECT CONTEXT

## 1. Project Overview
- JOBPI is an AI-assisted job application workspace that helps a user analyze job descriptions, maintain a personal CV library, compare CVs against roles, generate cover letters, and track application progress.
- Main goal: reduce manual effort in tailoring applications and make CV selection more consistent through AI-generated job analysis plus CV-role matching.
- Target users: individual job seekers managing multiple resumes and multiple active applications.
- Core functionality:
- User registration/login with JWT auth
- Upload one or many CV PDFs per user
- Extract CV text and generate compact CV library summaries
- Analyze a pasted job description into structured requirements and preparation guidance
- Match a selected CV to a job, compare two CVs for the same job, and generate improvement suggestions
- Generate a tailored cover letter from a job + selected CV
- Track application status and notes for each analyzed job

## 2. Tech Stack
### Backend
- FastAPI
- SQLModel on top of SQLAlchemy
- Pydantic
- Uvicorn
- PyMuPDF for PDF text extraction

### Frontend
- React 18
- TypeScript
- React Router
- Tailwind CSS
- Vite
- Lucide React icons

### Database
- PostgreSQL preferred for production, intended for Supabase
- SQLite fallback for local development

### AI / LLM (if exists)
- DSPy
- OpenRouter API
- Default model target: `openrouter/minimax/minimax-m2.5:free`

### DevOps / Deployment
- Local `.env`-driven configuration
- CORS-configured API
- Windows batch starter script (`iniciar.bat`)

### Other tools
- `jwt-decode` on frontend
- `python-dotenv`
- `python-multipart`

## 3. Architecture Overview
- Architecture style: modular monolith with a React SPA frontend and a single FastAPI backend.
- Backend layering is mostly:
- API routes for transport and validation
- dependencies for auth resolution
- services for business logic and AI orchestration
- db/crud for persistence access
- models/schemas for storage and API contracts
- Request flow:
1. Frontend page calls `frontend/src/services/api.ts`
2. FastAPI route validates request and enforces auth/rate/size limits
3. Service layer performs preprocessing, AI calls, caching, and CRUD operations
4. SQLModel persists user-scoped entities in SQLite or PostgreSQL
5. API returns normalized response DTOs consumed by the SPA
- The backend is not split into repository classes; `app/db/crud.py` acts as the data-access layer.
- AI-heavy features use service-level in-memory caches and DB reuse to avoid repeating expensive calls.

## 4. Folder Structure
- `app/`: FastAPI backend
- `app/api/routes/`: HTTP endpoints grouped by auth, CVs, jobs, matches
- `app/core/`: settings, AI helpers, security, rate limiting, request-size validation
- `app/db/`: engine/session setup, schema bootstrap, CRUD helpers
- `app/models/`: SQLModel table entities
- `app/schemas/`: request/response models exposed by the API
- `app/services/`: job analysis, CV analysis, cover-letter generation, PDF extraction, language handling
- `frontend/src/`: React SPA source
- `frontend/src/pages/`: top-level screens such as dashboard, job details, CV library, tracker
- `frontend/src/context/`: auth and language global state
- `frontend/src/services/`: frontend API client and response mappers
- `design-system/`: design reference material, not runtime code
- `frontend/dist/`: built frontend artifact already present in repo

## 5. Backend System
### Core modules
- `app/main.py`: creates FastAPI app, initializes schema on startup, registers routers, configures CORS, exposes `/health`.
- `app/core/settings.py`: single source of runtime configuration, env parsing, environment-specific limits, DSPy/OpenRouter setup.
- `app/core/ai.py`: shared AI timeout handling, LM token override context, provider error normalization.
- `app/core/security.py`: custom password hashing with PBKDF2-HMAC-SHA256 and custom HS256 JWT implementation.
- `app/dependencies/auth.py`: bearer-token auth dependency resolving current user from JWT subject.

### Business logic
- Job analysis:
- Cleans noisy job descriptions before AI calls
- Stores structured analysis in `job_analyses.analysis_result`
- Reuses existing analysis by normalized title/company/cleaned description and requested language
- Falls back to heuristic extraction when AI fails or times out
- CV library:
- Extracts text from PDF
- Cleans and truncates CV text
- Deduplicates by cleaned CV text per user
- Generates short CV library summaries
- Supports tags and deletion with cleanup of related matches/cover-letter links
- Matching:
- Evaluates a single CV against a job
- Persists `cv_job_matches`
- Computes an additional heuristic keyword-overlap score
- Can compare two CVs for the same job and explain the winner
- Cover letters:
- Generates concise role-specific plain-text cover letters
- Caches generated text on the related job record
- Tracking:
- Stores job status, optional applied date, and notes on each analyzed job

### Services
- `job_analyzer.py`: DSPy signature/module for structured job analysis plus fallback heuristics
- `cv_analyzer.py`: DSPy signature/module for CV-vs-job fit analysis
- `cv_library_service.py`: CV upload, matching, comparison, tag updates, serialization
- `cv_library_summary_service.py`: concise CV summary generation with heuristic fallback
- `cover_letter_service.py`: DSPy-based cover-letter generation and caching
- `pdf_extractor.py`: PDF validation, text extraction, cleanup, section focusing

### Utilities
- `job_preprocessing.py`: removes low-signal sections from job descriptions
- `response_language.py`: English/Spanish normalization and localized message helpers
- `rate_limit.py`: in-memory per-user/per-IP limiter
- `validation.py`: rejects oversized requests by `Content-Length`

## 6. API Endpoints
### Auth
- `POST /auth/register`: create user account
- `POST /auth/login`: authenticate and issue bearer token
- `GET /auth/me`: return current authenticated user

### CV
- `POST /cvs/upload`: upload a single PDF CV with display name
- `POST /cvs/batch-upload`: upload multiple PDF CVs in one request
- `GET /cvs`: list current user CVs
- `GET /cvs/{cv_id}`: get detailed CV data including raw/clean text
- `PATCH /cvs/{cv_id}/tags`: update CV tags
- `DELETE /cvs/{cv_id}`: delete CV and related match/cover-letter references

### Jobs
- `POST /jobs/analyze`: analyze a job description and persist a job-analysis record
- `GET /jobs`: list current user job analyses
- `GET /jobs/{job_id}`: get one analyzed job
- `PATCH /jobs/{job_id}/status`: update job application status and optional applied date
- `PATCH /jobs/{job_id}/notes`: update job notes
- `POST /jobs/{job_id}/match-cvs`: analyze one CV against one job
- `POST /jobs/{job_id}/compare-cvs`: compare two CVs for one job
- `POST /jobs/{job_id}/cover-letter`: generate or reuse cached cover letter for one job/CV pair

### Matches
- `GET /matches`: list all saved matches for current user
- `GET /matches/{match_id}`: get one saved match

### System
- `GET /health`: health check

## 7. Database Design
- ORM used: SQLModel with SQLAlchemy engine/session underneath.
- Main entities:
- `User`: email, hashed password, active flag, created timestamp
- `CV`: belongs to user; stores filename, display name, raw text, clean text, summary, library summary, tags
- `JobAnalysis`: belongs to user; stores job metadata, original and cleaned description, structured analysis JSON, status, notes, applied date, cached cover letter fields
- `CVJobMatch`: belongs to user and links one CV to one job; stores fit level, summary, strengths, missing skills, recommendation flag
- Relationships:
- `User 1 -> many CV`
- `User 1 -> many JobAnalysis`
- `User 1 -> many CVJobMatch`
- `CV 1 -> many CVJobMatch`
- `JobAnalysis 1 -> many CVJobMatch`
- `JobAnalysis.cover_letter_cv_id -> CV.id` is optional
- JSON storage:
- Uses generic JSON with PostgreSQL JSONB variant for arrays and analysis payloads
- `analysis_result` is the main persisted AI payload for jobs
- Migrations:
- No Alembic migration flow exists in the project codebase
- Schema is created at startup via `SQLModel.metadata.create_all`
- Additional compatibility changes are applied manually in `app/db/database.py` through runtime `ALTER TABLE` helpers, mainly for SQLite/dev legacy upgrades

## 8. Authentication & Security
- Authentication style: stateless bearer JWT.
- Login returns a custom HS256 JWT whose `sub` is currently user ID; auth dependency still supports legacy email-subject tokens.
- Password storage uses salted PBKDF2-HMAC-SHA256.
- Security middleware/dependencies:
- OAuth2 bearer parsing via `OAuth2PasswordBearer`
- `get_current_user` enforces valid token and active user
- User isolation:
- All CRUD reads/writes are filtered by `user_id`
- CVs, jobs, and matches are never fetched without user scoping
- Request protections:
- Configurable in-memory rate limits for auth, upload, job analysis, match, and cover-letter routes
- Request body size checks using `Content-Length`
- Environment-based stricter production limits
- CORS is configurable through `CORS_ORIGINS`
- Important limitation: rate limiting is in-memory only, so it is per-process and not shared across replicas.

## 9. AI / DSPy / LLM System (if exists)
- Provider path: DSPy -> OpenRouter -> configured model.
- Main DSPy signatures:
- `LeanJobAnalysisSignature`: extracts summary, seniority, skills, responsibilities, prep, learning path, gaps, resume/interview tips, project ideas
- `CvFitSignature`: returns fit summary, strengths, gaps, fit level, resume improvements, interview focus, next steps
- `CvLibrarySummarySignature`: creates short CV card summaries
- `CoverLetterSignature`: generates short plain-text tailored cover letters
- Flows:
- Job analysis first preprocesses noisy job text, then calls DSPy, then normalizes/truncates outputs
- CV matching sends cleaned job text + cleaned CV text and persists a reduced match record
- CV library summary uses AI when possible, otherwise heuristic role/tech detection
- Cover-letter generation uses job + selected CV summary/text and caches the result in the job row
- Providers/config:
- OpenRouter API key and base URL are required for AI
- Default model is configured by `DSPY_MODEL`
- Temperature is clamped into a narrow deterministic range
- Fallback behavior:
- Job analysis has a notable heuristic fallback path when AI fails or times out
- CV library summaries also have heuristic fallback
- CV matching and cover letters surface HTTP errors rather than full heuristic regeneration, except cached match reuse can be returned if a prior match exists

## 10. Environment Variables
- `APP_ENV`: selects `development` or `production` defaults
- `DATABASE_URL`: primary DB connection string; PostgreSQL required in production, SQLite fallback allowed only in development
- `SECRET_KEY`: JWT signing secret; `JWT_SECRET_KEY` is also supported as fallback input
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT lifetime
- `OPENROUTER_API_KEY`: required for AI features
- `OPENROUTER_BASE_URL`: OpenRouter endpoint
- `DSPY_MODEL`: target model identifier for DSPy/OpenRouter
- `DSPY_TEMPERATURE`: model temperature, later clamped by settings
- `MAX_OUTPUT_TOKENS`: shared output budget
- `JOB_ANALYSIS_MAX_TOKENS`: primary job-analysis token budget
- `JOB_ANALYSIS_RETRY_MAX_TOKENS`: smaller retry budget after timeout
- `JOB_PREPROCESS_TARGET_CHARS`: target input size after job cleanup
- `AI_TIMEOUT_SECONDS`: AI timeout
- `RATE_LIMIT_ENABLED`: enables/disables in-memory limiter
- `AUTH_RATE_LIMIT_WINDOW_SECONDS`: auth rate-limit window
- `AUTH_REGISTER_RATE_LIMIT`: auth registration cap
- `AUTH_LOGIN_RATE_LIMIT`: auth login cap
- `JOB_ANALYZE_RATE_LIMIT_WINDOW_SECONDS`: job-analysis rate-limit window
- `JOB_ANALYZE_RATE_LIMIT`: job-analysis cap
- `MATCH_CVS_RATE_LIMIT_WINDOW_SECONDS`: match rate-limit window
- `MATCH_CVS_RATE_LIMIT`: match cap
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
