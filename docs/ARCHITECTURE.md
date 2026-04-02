# ARCHITECTURE

## Folder Structure

- `app/api/routes/`: HTTP endpoints for auth, CVs, jobs, and matches.
- `app/core/`: runtime settings, AI helpers, security, rate limiting, validation.
- `app/db/`: engine/session setup, schema bootstrap, CRUD helpers.
- `app/dependencies/`: request-scoped dependencies such as current-user resolution.
- `app/models/`: SQLModel entities.
- `app/schemas/`: request and response models.
- `app/services/`: PDF extraction, job analysis, CV matching, summaries, cover letters.
- `frontend/src/pages/`: routed screens.
- `frontend/src/components/`: shared UI and layout components.
- `frontend/src/services/`: API client and mapping helpers.

## Request Flow

1. A frontend page calls the API client in `frontend/src/services/api.ts`.
2. The FastAPI route validates the payload and applies size or rate checks where needed.
3. The service layer performs preprocessing, AI calls, persistence, and response shaping.
4. SQLModel stores or reads user-scoped data through the database layer.
5. The frontend renders normalized DTOs returned by the backend.

## Auth Flow

1. User submits credentials to `/auth/login` or creates an account through `/auth/register`.
2. Login returns a bearer token.
3. The frontend stores the token and sends it on protected requests.
4. The backend resolves the current user from the token subject.
5. All CV, job, and match operations remain scoped to that user.

## Database Flow

- `users` stores the account identity and password hash.
- `cvs` stores uploaded CV files, extracted text, summary text, and tags.
- `job_analyses` stores the raw and cleaned job description, structured analysis, status, notes, and cached cover-letter data.
- `cv_job_matches` stores job-to-CV fit results and recommended match data.
- SQLite is supported locally, but PostgreSQL is the production target.

## Deployment Architecture

- Backend deployment entrypoint: `api/index.py`.
- Frontend deployment: Vite build output hosted separately or on the same platform with `VITE_API_URL` pointing to the backend.
- Vercel rewrites route all requests to the Python entrypoint in this repository.
- Supabase provides the hosted production database.

## Notes

- Runtime schema creation is handled on backend startup.
- AI features are routed through DSPy with OpenRouter as the provider.
- Production uses stricter rate limits and smaller upload budgets than local development.