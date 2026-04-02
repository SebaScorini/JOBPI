# ENVIRONMENT

This project reads environment variables from both backend and frontend code.

## Backend Variables

| Variable | Purpose | Notes |
| --- | --- | --- |
| `APP_ENV` | Selects development or production defaults | Defaults to `development` |
| `DATABASE_URL` | SQLAlchemy connection string | Required in production; SQLite fallback allowed locally |
| `SECRET_KEY` | JWT signing secret | `JWT_SECRET_KEY` is accepted as a fallback source |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime | Defaults to 60 |
| `OPENROUTER_API_KEY` | OpenRouter auth key | Required for AI features |
| `OPENROUTER_BASE_URL` | OpenRouter API base URL | Defaults to `https://openrouter.ai/api/v1` |
| `SENTRY_DSN` | Enables backend error reporting to Sentry | Optional; leave unset to disable Sentry |
| `REDIS_URL` | Enables shared Redis-backed rate limiting | Optional; in-memory fallback remains available |
| `DSPY_MODEL` | DSPy model identifier | Defaults to `openrouter/minimax/minimax-m2.5:free` |
| `DSPY_TEMPERATURE` | Model temperature | Clamped to a narrow safe range |
| `MAX_OUTPUT_TOKENS` | Shared output budget | `DSPY_MAX_TOKENS` is also accepted as a fallback source |
| `JOB_ANALYSIS_MAX_TOKENS` | Job-analysis token budget | Higher ceiling than shared output budget |
| `JOB_ANALYSIS_RETRY_MAX_TOKENS` | Retry token budget for job analysis | Capped by `JOB_ANALYSIS_MAX_TOKENS` |
| `JOB_PREPROCESS_TARGET_CHARS` | Target job-description size after cleanup | Used before AI calls |
| `AI_TIMEOUT_SECONDS` | Timeout for AI operations | `DSPY_TIMEOUT_SECONDS` is also accepted as a fallback source |
| `RATE_LIMIT_ENABLED` | Enables in-memory rate limiting | Defaults depend on `APP_ENV` |
| `TRUSTED_USER_EMAIL` | Bypasses some user limits for one email | Compared case-insensitively |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | Auth rate-limit window | Defaults depend on environment |
| `AUTH_REGISTER_RATE_LIMIT` | Register rate-limit cap | Defaults depend on environment |
| `AUTH_LOGIN_RATE_LIMIT` | Login rate-limit cap | Defaults depend on environment |
| `JOB_ANALYZE_RATE_LIMIT_WINDOW_SECONDS` | Job-analysis rate-limit window | Defaults depend on environment |
| `JOB_ANALYZE_RATE_LIMIT` | Job-analysis rate-limit cap | Defaults depend on environment |
| `MATCH_CVS_RATE_LIMIT_WINDOW_SECONDS` | Match rate-limit window | Defaults depend on environment |
| `MATCH_CVS_RATE_LIMIT` | Match rate-limit cap | Defaults depend on environment |
| `COVER_LETTER_RATE_LIMIT_WINDOW_SECONDS` | Cover-letter rate-limit window | Defaults depend on environment |
| `COVER_LETTER_RATE_LIMIT` | Cover-letter rate-limit cap | Defaults depend on environment |
| `CV_UPLOAD_RATE_LIMIT_WINDOW_SECONDS` | CV-upload rate-limit window | Defaults depend on environment |
| `CV_UPLOAD_RATE_LIMIT` | CV-upload rate-limit cap | Defaults depend on environment |
| `MAX_PDF_SIZE_MB` | Maximum upload size per PDF | Defaults depend on environment |
| `MAX_CVS_PER_UPLOAD` | Maximum files per batch upload | Defaults depend on environment |
| `MAX_JOB_DESCRIPTION_CHARS` | Maximum job-description length | Defaults depend on environment |
| `MAX_CV_TEXT_CHARS` | Maximum extracted CV text length | Defaults depend on environment |
| `SQLITE_TIMEOUT_SECONDS` | SQLite connection timeout | Local development only |
| `FRONTEND_URL` | Primary frontend URL | Added to CORS origins automatically |
| `CORS_ORIGINS` | Allowed browser origins | Comma-separated list |
| `CORS_ORIGIN_REGEX` | Allowed origin regex | Useful for preview deployments |
| `CORS_MAX_AGE_SECONDS` | CORS preflight cache age | Defaults to 600 |

## Frontend Variables

| Variable | Purpose | Notes |
| --- | --- | --- |
| `VITE_API_URL` | Backend base URL for the SPA | Required in production deployments |
| `VITE_SITE_URL` | Canonical site origin | Used for SEO metadata and canonical links |

## Example Files

- Root example values: [`.env.example`](../.env.example)
- Deployment sync helper: [`sync_vercel_envs.py`](../sync_vercel_envs.py)

## Notes

- Keep `DATABASE_URL` on PostgreSQL in production.
- Keep `SECRET_KEY` and `OPENROUTER_API_KEY` out of source control.
- Set `SENTRY_DSN` only in environments where Sentry ingestion is intended.
- Set `REDIS_URL` in production to enable cross-instance rate limiting.
- Use `CORS_ORIGIN_REGEX` for preview URLs instead of wildcard origins.
