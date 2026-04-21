# ENVIRONMENT

This document lists all environment variables currently referenced in application code.

## Backend Variables

| Variable | Required | Purpose | Notes |
| --- | --- | --- | --- |
| `APP_ENV` | No | Select runtime profile (`development`, `production`) | Defaults to `development` |
| `DATABASE_URL` | Yes (prod) | SQLAlchemy connection URL | Development defaults to local SQLite path |
| `SECRET_KEY` | Yes (prod) | JWT signing key | Fallback source: `JWT_SECRET_KEY` |
| `JWT_SECRET_KEY` | No | Legacy fallback for JWT signing key | Used only if `SECRET_KEY` is missing |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Access-token lifetime | Default `60` |
| `OPENROUTER_API_KEY` | Yes (AI features) | OpenRouter API authentication | Required for DSPy-backed AI endpoints |
| `OPENROUTER_BASE_URL` | No | OpenRouter base URL | Default `https://openrouter.ai/api/v1` |
| `DSPY_MODEL` | No | DSPy model identifier | Default `openrouter/minimax/minimax-m2.5:free` |
| `DSPY_TEMPERATURE` | No | Model temperature | Clamped in code to safe range |
| `MAX_OUTPUT_TOKENS` | No | Shared AI output token cap | Fallback source: `DSPY_MAX_TOKENS` |
| `DSPY_MAX_TOKENS` | No | Legacy fallback token cap | Used only if `MAX_OUTPUT_TOKENS` is missing |
| `JOB_ANALYSIS_MAX_TOKENS` | No | Token cap for job-analysis generation | Bound to max limits in code |
| `JOB_ANALYSIS_RETRY_MAX_TOKENS` | No | Retry token cap for job-analysis fallback | Capped by `JOB_ANALYSIS_MAX_TOKENS` |
| `JOB_PREPROCESS_TARGET_CHARS` | No | Target cleaned job-description size | Used before AI generation |
| `AI_TIMEOUT_SECONDS` | No | Timeout for AI operations | Fallback source: `DSPY_TIMEOUT_SECONDS` |
| `DSPY_TIMEOUT_SECONDS` | No | Legacy AI-timeout fallback | Used only if `AI_TIMEOUT_SECONDS` is missing |
| `SENTRY_DSN` | No | Enables Sentry error reporting | If unset, Sentry is disabled |
| `REDIS_URL` | No | Enables Redis-backed distributed rate limiting | In-memory fallback remains available |
| `RATE_LIMIT_ENABLED` | No | Enables/disables rate limiting | Environment defaults differ by profile |
| `TRUSTED_USER_EMAIL` | No | Allows user-limit bypass for one account | Case-insensitive comparison |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | No | Auth window duration | Applies to register/login policies |
| `AUTH_REGISTER_RATE_LIMIT` | No | Register attempt cap per window | Profile-based default |
| `AUTH_LOGIN_RATE_LIMIT` | No | Login attempt cap per window | Profile-based default |
| `JOB_ANALYZE_RATE_LIMIT_WINDOW_SECONDS` | No | Job-analysis window duration | Profile-based default |
| `JOB_ANALYZE_RATE_LIMIT` | No | Job-analysis cap per window | Profile-based default |
| `MATCH_CVS_RATE_LIMIT_WINDOW_SECONDS` | No | Match endpoint window duration | Profile-based default |
| `MATCH_CVS_RATE_LIMIT` | No | Match endpoint cap per window | Profile-based default |
| `COVER_LETTER_RATE_LIMIT_WINDOW_SECONDS` | No | Cover-letter window duration | Profile-based default |
| `COVER_LETTER_RATE_LIMIT` | No | Cover-letter cap per window | Profile-based default |
| `CV_UPLOAD_RATE_LIMIT_WINDOW_SECONDS` | No | CV upload window duration | Profile-based default |
| `CV_UPLOAD_RATE_LIMIT` | No | CV upload cap per window | Profile-based default |
| `MAX_PDF_SIZE_MB` | No | Max size per uploaded PDF | Profile-based default |
| `MAX_CVS_PER_UPLOAD` | No | Max PDFs per batch request | Profile-based default |
| `MAX_JOB_DESCRIPTION_CHARS` | No | Max job-description length | Profile-based default |
| `MAX_CV_TEXT_CHARS` | No | Max extracted CV text length | Profile-based default |
| `SQLITE_TIMEOUT_SECONDS` | No | SQLite busy-timeout seconds | Local database behavior |
| `FRONTEND_URL` | No | Primary frontend origin | Auto-added to CORS origins |
| `CORS_ORIGINS` | No | Explicit allowed origins list | Comma-separated |
| `CORS_ORIGIN_REGEX` | No | Regex for allowed origins | Recommended for preview domains |
| `CORS_MAX_AGE_SECONDS` | No | CORS preflight cache max age | Default `600` |

## Runtime/Platform Variables

| Variable | Required | Purpose | Notes |
| --- | --- | --- | --- |
| `VERCEL` | Platform-managed | Detect Vercel runtime | Used to set default DSPy cache path |
| `DSPY_CACHEDIR` | No | DSPy cache location | Auto-set to `/tmp/.dspy_cache` on Vercel if missing |

## Frontend Variables

| Variable | Required | Purpose | Notes |
| --- | --- | --- | --- |
| `VITE_API_URL` | Yes (prod frontend) | Backend base URL for SPA requests | Local fallback logic exists for localhost and default hosted API |
| `VITE_SITE_URL` | No | Canonical site URL for frontend canonical URLs and password-reset redirects | Included in `.env.example` for hosted deployments; the frontend falls back to the browser origin when available |

## Example Sources

- Root env template: [`.env.example`](../.env.example)
- Vercel env helper script: [`sync_vercel_envs.py`](../sync_vercel_envs.py)
- Deployment guide: [`docs/DEPLOYMENT.md`](DEPLOYMENT.md)

## Operational Notes

- Production must use PostgreSQL via `DATABASE_URL`.
- `SECRET_KEY` must be explicitly set in production.
- Keep `OPENROUTER_API_KEY`, `SECRET_KEY`, and database credentials out of source control.
- Use `REDIS_URL` in multi-instance production environments to avoid per-instance limiter drift.
- Prefer `CORS_ORIGIN_REGEX` for preview URLs rather than broad wildcard origin rules.
- `VITE_API_URL` is the primary frontend runtime setting for backend requests.
- `VITE_SITE_URL` is also read by the frontend for canonical URLs and password-reset redirects when the browser origin is not available.
