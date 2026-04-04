# JOBPI SPRINT ROADMAP: EXECUTABLE PLAN

## Recommended Sprint Sequence

```
Sprint 0 (1 week)  → Foundation & Observability
    ↓
Sprint 1 (2 weeks) → Critical Backend Fixes
    ↓
Sprint 2 (2 weeks) → Data Layer & Migrations
    ↓
Sprint 3 (2 weeks) → API Improvements & Scaling
    ↓
Sprint 4 (2 weeks) → Frontend Polish & UX
    ↓
Sprint 5 (1 week)  → Quick-Win Features
    ↓
Sprint 6 (2 weeks) → Reliability & Testing
    ↓
Sprint 7 (2 weeks) → Advanced Features (Monetization)

Total: ~14 weeks to production-ready SaaS platform
```

---

## **SPRINT 0 — Foundation & Observability** (1 week)

### Objective
Establish baseline observability and fix quick-win bugs before scaling work. Make the project safe to observe and debug in production.

### Why This Matters
- **Technical**: Can't improve what you can't see. Need logs, error tracking, and monitoring before making large changes.
- **Business**: Fixes encoding issues (trust/UX signal) + establishes metrics baseline for measuring improvements.
- **Portfolio**: Demonstrates operations maturity; observability is a professional signal.

### Tasks

#### Task 1: Fix Frontend Encoding Mojibake (30 min)
**What**: Audit frontend `.tsx` files for garbled Unicode strings and fix them.
- Search for encoding artifacts (✓, ?, corrupted text)
- Target files: `frontend/src/components/`, `frontend/src/pages/`, `frontend/src/i18n/translations.ts`
- Replace with proper UTF-8 strings

**Why**: Users see broken characters → low trust; also indicates code quality issues.

---

#### Task 2: Add Structured JSON Logging to Backend (90 min)
**What**: Replace ad-hoc console logs with structured JSON logging + middleware trace tracking.
- Install `python-json-logger`
- Create `app/core/logging.py` with JSON logger setup
- Add middleware to `app/main.py` that:
  - Generates `trace_id` (UUID) for every request
  - Logs request start: `{ trace_id, method, path, user_id, timestamp }`
  - Logs request end: `{ trace_id, status, duration_ms, timestamp }`
- Wrap exception handler to log errors with trace_id to JSON
- Test output: verify logs are valid JSON (parseable by tools like `jq`)

**Why**: Foundation for observability; allows correlation of errors across services; enables better debugging in production.

---

#### Task 3: Integrate Sentry Error Tracking (60 min)
**What**: Add optional Sentry integration for error aggregation and alerting.
- Install `sentry-sdk`
- Initialize in `app/main.py` if `SENTRY_DSN` env var is present (else no-op)
- Add custom context to every error: `{ user_id, trace_id, path, body_size }`
- Suppress known non-errors (rate limit 429s, expected validation errors)
- Document setup in `docs/ENVIRONMENT.md`: "Set `SENTRY_DSN=https://...@sentry.io/..." to enable"

**Why**: Gain visibility into production errors + trends without building custom dashboards; alerting for critical issues.

---

#### Task 4: Increase Cover Letter Rate Limit (Development) (15 min)
**What**: Bump development rate limits to reduce friction during feature work.
- Change `ENV_DEFAULTS["development"]["cover_letter_limit"]` from 4 to 6/hour
- Change `cover_letter_window_seconds` from 300 to 600 (broader window for dev)
- Add code comment: "Dev limits are loose; production uses 4/hour for cost control"

**Why**: Quick win; improves dev iteration speed without affecting production.

---

#### Task 5: Audit & Document Current Rate Limit Configuration (45 min)
**What**: Document current rate limiting state before replacing it (Sprint 1).
- Create `docs/RATE_LIMITING.md`:
  - List all policies (Auth, CV Upload, Job Analyze, Match, Cover Letter)
  - Document dev values vs. production values
  - Explain current in-memory deque implementation
  - Note: "Single-process only; will replace with Redis in Sprint 1"
- Add inline code comment in `app/core/rate_limit.py` linking to this doc

**Why**: Baseline documentation; helps with migration planning in Sprint 1.

---

#### Task 6: Create Production Health Check Checklist (30 min)
**What**: Document what needs to be verified after every deployment.
- Create `docs/HEALTH_CHECK.md`:
  - Health endpoint: `curl https://api.jobpi.app/health`
  - DB connectivity: Can write/read from Supabase
  - Auth flow: Can register and login
  - AI integration: Can call DSPy (may be cached test)
  - Rate limiting: Verify 429s after limit exceeded
  - Logging: Check Sentry dashboard for errors
- Add as pre-deploy checklist in CI/CD (or manual checklist in README)

**Why**: Catches deployment issues early; part of professional DevOps practice.

---

### Dependencies
- Existing FastAPI app running
- `requirements.txt` can be modified
- Supabase/PostgreSQL or SQLite running
- Frontend repo accessible

### Risks
- **Logging volume**: JSON logging may increase CloudWatch/Vercel costs; recommend sampling in production (`sample_rate=0.1` for non-errors)
- **Sentry account**: Requires API key; can be skipped locally
- **Backward compat**: New logging format doesn't break existing tools (none expected)

### Implementation Order
1. Fix encoding issues (quick win; unblocked)
2. Add JSON logging middleware (required for observability)
3. Integrate Sentry (can be skipped if no API key)
4. Increase dev rate limits (cosmetic; no risk)
5. Audit & document rate limiting (prep for Sprint 1)
6. Create health check checklist (reference for all future sprints)

### Testing Checklist
- [ ] Frontend renders correctly with fixed encoding (no garbled text in UI)
- [ ] Backend logs are valid JSON: `curl http://localhost:8000/health | jq '.' ` exits 0
- [ ] Trace ID appears in every log line
- [ ] Sentry dashboard shows test errors when sent
- [ ] All 4 endpoints (auth, cvs, jobs, matches)  accept requests and log them
- [ ] Rate limit policies still enforced in dev mode
- [ ] No regression: existing tests pass (run `pytest`)

### Deployment Checklist
- [ ] `.env` does not need update (logging changes are backward compatible)
- [ ] No DB migrations needed
- [ ] `requirements.txt` updated with `python-json-logger` and `sentry-sdk`
- [ ] `app/core/logging.py` added
- [ ] `app/main.py` middleware added (test locally first)
- [ ] `docs/RATE_LIMITING.md` and `docs/HEALTH_CHECK.md` added
- [ ] Run `docker compose up` locally; verify logs are JSON format
- [ ] Deploy to staging first; verify Sentry captures test error
- [ ] Run health check; compare baseline metrics
- [ ] Deploy to production; monitor logs for 15 min

### Definition of Done
- ✅ Frontend has no visible encoding mojibake
- ✅ All backend logs are valid JSON with trace IDs
- ✅ Sentry dashboard (or offline fallback) captures errors
- ✅ Development rate limit bumped to 6/hour
- ✅ Rate limiting and health check documentation in place
- ✅ All existing tests pass
- ✅ No performance regression (measure latency of `/health` endpoint baseline)

---

### Codex Prompts

#### **Codex Planning Prompt**
```
Plan Sprint 0 (Foundation & Observability):
1. Search frontend src/ for encoding mojibake (UTF-8 artifacts)
2. Identify where encoding happens in translations
3. Review current logging in app/ (find all print() or logger.info() calls)
4. Sketch JSON logger structure: { trace_id, timestamp, level, message, context }
5. Identify all rate limit policies and document current values
6. Outline Sentry integration: init, context setting, error suppression
7. List health check scenarios (auth, upload, analyze, match, coverage)
8. Propose file structure: new files to create (logging.py, docs/RATE_LIMITING.md, docs/HEALTH_CHECK.md)
9. Estimate effort per task
10. Identify any blocking dependencies
```

#### **Codex Implementation Prompt**
```
Implement Sprint 0:

PART 1 — Encoding Fixes (30 min)
1. Search frontend/src for mojibake patterns:
   - Find: [✓ (U+2713), ✗ (U+2717), corrupted accents, garbled Unicode]
   - Files to check: LanguageSelector.tsx, layout/, pages/, i18n/translations.ts
   - For each: replace with proper UTF-8 or remove if unnecessary
   - Test: npm run build; no warnings

PART 2 — JSON Logging (90 min)
1. Create app/core/logging.py:
   - Import logging, json, python_json_logger
   - Create setup_logging() function
   - Configure JSON formatter for all handlers
   - Test: log.info("test", extra={"key": "value"}) → valid JSON
2. Update app/main.py:
   - Import setup_logging(); call in create_app()
   - Add middleware to generate trace_id (UUID)
   - Log request_start and request_end with trace_id
   - Wrap app.add_exception_handler() to log errors with trace_id
3. Test locally:
   - Start backend: make up
   - Use curl to hit /auth/register; check logs are JSON
   - Parse logs with jq: docker compose exec backend tail -f logs | jq '.'

PART 3 — Sentry Integration (60 min)
1. Update requirements.txt: add sentry-sdk
2. Update app/core/settings.py:
   - Add sentry_dsn: str | None field
   - Read from env: SENTRY_DSN (default None)
3. Update app/main.py:
   - If sentry_dsn is set, init sentry:
     import sentry_sdk
     sentry_sdk.init(sentry_dsn, traces_sample_rate=0.1)
   - Add capture_exception() on HTTPException
   - Test: trigger 500 error; check Sentry dashboard
4. Document in docs/ENVIRONMENT.md

PART 4 — Rate Limit Tuning (15 min)
1. Update app/core/settings.py:
   - ENV_DEFAULTS["development"]["cover_letter_limit"] = 6
   - ENV_DEFAULTS["development"]["cover_letter_window_seconds"] = 600
2. Add inline comment: "Development use only; production is stricter"

PART 5 — Documentation (45 min)
1. Create docs/RATE_LIMITING.md:
   - List all policies with dev + prod values
   - Explain current implementation (in-memory deque)
   - Schedule for Redis swap in Sprint 1
2. Create docs/HEALTH_CHECK.md:
   - Test endpoints: /health, /auth/me, /cvs, /jobs, /matches
   - Sample curl commands
   - Expected responses
   - Error scenarios

PART 6 — Testing (60 min)
1. Local:
   - make up; verify Docker compose runs
   - curl http://localhost:8000/health → JSON logs
   - Trigger error; check logs + Sentry
   - Run pytest; ensure no regression
2. Staging:
   - Deploy to staging branch
   - Run smoke tests
3. Production:
   - Deploy to main
   - Monitor Sentry + logs for 30 min
```

#### **Codex Testing Prompt**
```
Test Sprint 0 Deliverables:

LOCAL TESTING (run before commit):
1. Frontend encoding (30 min):
   - cd frontend
   - npm run tsc (TypeScript check)
   - npm run build (Vite build)
   - npm run lint (ESLint check)
   - Search for mojibake in dist/ (verify not copied)

2. Backend logging (60 min):
   - Start Docker: make up
   - Test health endpoint:
     curl http://localhost:8000/health
     → Verify response is JSON with status: ok
   - Check logs:
     docker compose logs backend | head -20
     → Must be valid JSON lines (passable to jq)
   - Verify trace_id in every log:
     docker compose logs backend | jq '.trace_id' | sort | uniq | wc -l
     → Should have multiple trace_ids

3. Sentry integration (skip if no SENTRY_DSN):
   - Create test account on sentry.io (or use staging)
   - Set SENTRY_DSN=https://<key>@sentry.io/<project>
   - Restart backend: make restart
   - Trigger 500 error:
     curl http://localhost:8000/auth/me (no auth header)
     → Should be 401, logged to Sentry
   - Check Sentry dashboard: see error captured

4. Rate limits (30 min):
   - Read app/core/settings.py:
     ENV_DEFAULTS["development"]["cover_letter_limit"] == 6 ✓
   - Start a dev session:
     python -c "from app.core.config import get_settings; s=get_settings(); print(s.cover_letter_limit)"
     → Should print 6

5. Regression (30 min):
   - Run pytest:
     pytest
     → All tests pass
   - No new warnings in TypeScript or Python

MANUAL VERIFICATION:
1. Open http://localhost:3000 (frontend)
   - No visible encoding errors in text or UI
   - Can register new account
   - Can log in
2. Check logs while navigating:
   - Each page load creates request_start + request_end logs
   - Trace IDs are consistent per request

POST-DEPLOY (production):
1. Verify health endpoint:
   curl https://jobpi-api.vercel.app/health
2. Check Sentry dashboard (if configured):
   - No new error spikes
   - Expected errors captured
3. Check logs in Vercel dashboard:
   - Sample logs are valid JSON
```

#### **Codex Deployment Verification Prompt**
```
Deploy & Verify Sprint 0:

PRE-DEPLOYMENT:
1. Code review:
   - All encoding fixes reviewed
   - JSON logger correct format
   - Sentry integration has fallback (no-op if no DSN)
   - Rate limit changes verified
2. Build check:
   - Backend: docker compose build backend (no errors)
   - Frontend: cd frontend && npm run build (no errors)
3. Local smoke test:
   - docker compose up; wait 30s
   - curl http://localhost:8000/health → 200 OK
   - curl http://localhost:3000 (frontend loads)

DEPLOYMENT STEPS:
1. Staging deployment (optional):
   - Deploy to staging branch on Vercel
   - Run health check (see docs/HEALTH_CHECK.md)
   - Monitor logs for 5 min
   - Verify no errors in Sentry (if configured)

2. Production deployment:
   - Merge to main
   - Vercel auto-deploys
   - Monitor Sentry + Vercel logs (15 min)
   - Check error count baseline

HEALTH CHECK (POST-DEPLOY):
1. API endpoints:
   - GET /health → { "status": "ok" }
   - POST /auth/login with bad creds → 401 (logged)
   - GET /cvs (with valid token) → { items: [...] }
   
2. Logging verification:
   - Check Vercel/CloudWatch logs → JSON format ✓
   - Trace IDs present ✓
   - No format errors ✓

3. Sentry (if configured):
   - Dashboard shows 0 new errors (or expected error count)
   - Error sampling working (if set to 0.1)

4. Performance baseline:
   - /health latency: <50ms (measure 5 times, avg)
   - /cvs latency (auth required): <200ms (if DB healthy)
   - Record as baseline for future sprints

ROLLBACK (if issues):
1. If logs not valid JSON:
   - Revert logging.py changes
   - Redeploy
2. If Sentry DSN not configured:
   - No-op; safe to leave
   - Easy to configure later
3. If rate limits wrong:
   - Update ENV_DEFAULTS
   - Redeploy
   → All changes are safe reversions

POST-DEPLOYMENT ACTIONS:
- Document baseline metrics (latency, error rate)
- Share log sample with team (show JSON format)
- Schedule Sprint 1 kickoff (Redis rate limiting next)
```

---

## **SPRINT 1 — Critical Backend Fixes** (2 weeks)

### Objective
Fix production-blocking issues in the backend that will prevent scaling. Implement circuit breaker for AI calls, prepare for Redis rate limiting, and upgrade JWT security.

### Why This Matters
- **Technical**: Three critical blockers for production: (1) in-memory rate limiting breaks at scale, (2) DSPy token bleed on retries, (3) custom JWT is a security audit risk
- **Business**: Can't reliably run without these fixes; needed for any paid tier or user growth
- **Portfolio**: Demonstrates understanding of resilience patterns, security hardening, and distributed systems constraints

### Tasks

#### Task 1: Implement Circuit Breaker for DSPy LM Calls (180 min)
**What**: Wrap all DSPy LM calls with exponential backoff and max-retry cap to prevent token budget bleed.

**Why**: 
- Current: If DSPy fails, retry loop can exhaust token budget before giving up
- After: Fail fast after 3 retries; log circuit breaker events for monitoring

**Details**:
1. Create `app/core/circuit_breaker.py`:
   - `CircuitBreakerConfig`: max_retries (3), initial_backoff_ms (100), max_backoff_ms (5000)
   - `AICircuitBreaker` class wrapping dspy.invoke()
   - Exponential backoff: delay * 2^retry, capped at max_backoff
   - Log on each retry: `{ operation: "job_analysis", retry: 1, delay_ms: 200, tokens_used: 541 }`
   - When max retries exceeded, raise `CircuitBreakerOpenError` with clear message

2. Update all AI calls:
   - `app/services/job_analyzer.py`: wrap `LeanJobAnalysisSignature` invocation
   - `app/services/cv_analyzer.py`: wrap `CvFitModule` invocation
   - `app/services/cv_library_summary_service.py`: wrap summary generation
   - `app/services/cover_letter_service.py`: wrap cover letter generation

3. Testing:
   - Unit test: Circuit breaker retries 3 times then fails
   - Mock DSPy: simulate timeout on 1–2 attempts, succeed on 3rd
   - Verify backoff delays are exponential
   - Verify logs contain retry count and token usage

---

#### Task 2: Prepare Redis-Based Rate Limiter (240 min)
**What**: Implement a Redis-backed rate limiter that can scale across multiple Vercel instances.

**Why**: 
- Current: In-memory deque; only works on single instance
- After: Can scale to N instances; shared rate limit state across processes

**Details**:
1. Create `app/core/rate_limit_redis.py`:
   - `RedisRateLimiter` class (similar to current `InMemoryRateLimiter`)
   - Use Redis key format: `ratelimit:{policy_name}:{subject_key}` with TTL=window_seconds
   - Increment counter; check if >= limit
   - Return retry-after header (seconds until limit resets)
   - Fallback: If Redis unavailable (connection error), log warning and allow request (fail-open)

2. Update `app/core/rate_limit.py`:
   - Add factory: `get_rate_limiter()` → returns Redis or In-Memory based on env
   - Keep both implementations active (swap via REDIS_URL env var)
   - If REDIS_URL not set, use in-memory (for dev/testing)
   - If set, use Redis (for production)

3. Add to `requirements.txt`:
   - `redis>=5.0`
   - `aioredis` (optional, for async operations)

4. Update `docs/ENVIRONMENT.md`:
   - Document REDIS_URL format: `redis://default:password@host:port/db`
   - How to get Upstash Redis URL (free tier)
   - Fallback behavior (in-memory if Redis unavailable)

5. Testing:
   - Unit tests: rate limiter enforces limit correctly with Redis
   - Integration test: start Redis container, verify rate limiting works
   - Failover test: disconnect Redis, verify fallback to in-memory
   - Load test: 100 concurrent requests to same endpoint; verify enforced

---

#### Task 3: Upgrade JWT to Use PyJWT Library (120 min)
**What**: Replace custom JWT implementation with industry-standard PyJWT library while maintaining backward compatibility.

**Why**:
- Current: Custom JWT implementation (home-grown, smaller attack surface but less audited)
- After: PyJWT is battle-tested; easier to audit; standard library calls look better in hiring
- Concern: Need to support old tokens during rollout

**Details**:
1. Add to `requirements.txt`:
   - `pyjwt>=2.8.0`

2. Update `app/core/security.py`:
   - Replace `_encode_jwt()` with `jwt.encode()` using PyJWT
   - Replace `_decode_jwt()` with `jwt.decode()` using PyJWT
   - Keep old decode logic as fallback (for tokens signed with old code)
   - Algorithm: HS256 (same as custom)
   - Document the transition period: "Old tokens valid for 30 days after deploy"

3. Testing:
   - Decode old token (signed by custom code) → verify PyJWT can read it (or use fallback)
   - Encode new token with PyJWT → verify custom decoder can read it (backward compat)
   - Expiry logic unchanged
   - Error messages same (credentials error on invalid token)

4. Deployment strategy:
   - Deploy new code (PyJWT + fallback for old tokens)
   - Old tokens still work for 30 days (custom decode fallback)
   - 30 days later, remove custom fallback
   - Recommendation: Users don't notice anything

---

#### Task 4: Enhance Error Handling with Structured Error Codes (90 min)
**What**: Add standardized error codes and messages for better frontend retries and debugging.

**Why**: Frontend can't distinguish between "rate limit" vs "AI timeout" vs "auth error" without parsing error text.

**Details**:
1. Create `app/core/error_codes.py`:
   ```python
   class ErrorCode(Enum):
       RATE_LIMIT = "ERR_RATE_LIMIT"
       AI_TIMEOUT = "ERR_AI_TIMEOUT"
       AUTH_INVALID = "ERR_AUTH_INVALID"
       CV_NOT_FOUND = "ERR_CV_NOT_FOUND"
       JOB_NOT_FOUND = "ERR_JOB_NOT_FOUND"
       PDF_INVALID = "ERR_PDF_INVALID"
       CIRCUIT_BREAKER_OPEN = "ERR_CIRCUIT_BREAKER_OPEN"
       DB_ERROR = "ERR_DB_ERROR"
   ```

2. Update all error-throwing routes:
   - Rate limit: include error code + retry-after
   - AI timeouts: include error code
   - Auth errors: include error code
   - 404s: include error code

3. Update frontend `api.ts`:
   - Parse error code from response
   - Implement retry logic: if RATE_LIMIT, wait retry-after; if AI_TIMEOUT, suggest manual retry
   - Log error code + message to Sentry for aggregation

4. Testing:
   - Each error scenario triggers correct error code
   - Frontend can parse and act on error code
   - Sentry shows error codes aggregated

---

#### Task 5: Add Comprehensive Logging to AI Service Layer (120 min)
**What**: Log AI operations (input size, output, tokens, latency, errors) for cost tracking and debugging.

**Why**: 
- Current: No visibility into token spend or AI operation latency
- After: Can see: "Job analysis took 3.2s, used 541 tokens, cost $0.01"

**Details**:
1. Update `app/services/job_analyzer.py`:
   - Before invoke: log `{ operation: "job_analysis", title, company, input_chars, response_language, start: timestamp }`
   - After invoke: log `{ operation: "job_analysis", output_tokens, execution_ms, end: timestamp }`
   - On error: log `{ operation: "job_analysis", error, error_type, retry_count }`

2. Same for:
   - `cv_analyzer.py`: CV fit analysis
   - `cover_letter_service.py`: Cover letter generation
   - `cv_library_summary_service.py`: CV summary generation

3. Create `app/core/telemetry.py`:
   - `log_ai_operation()`: helper to log standardized AI operation details
   - Tracks: operation name, input/output size, tokens, latency, cost
   - Aggregatable for monthly cost reports

4. Testing:
   - Call each AI service; verify logs are created
   - Check log format: valid JSON with all expected fields
   - Verify cost calculation is correct (tokens × rate)

---

### Dependencies
- Sprint 0 complete (logging setup)
- Backend running with Docker
- Redis instance available (or Upstash account for production)
- PyJWT library compatible with current Python version

### Risks
- **JWT Rollover**: Old tokens must remain valid during transition; test carefully
- **Redis Availability**: If Redis unavailable, fallback to in-memory (but loses cross-instance limiting); log this clearly
- **Circuit Breaker Too Aggressive**: If max_retries=3 too low, genuine transient failures fail fast; monitor and adjust
- **Token Costs**: Detailed logging may increase API costs if enabled for all requests; use sampling

### Implementation Order
1. Circuit breaker (Sprints 2–7 depend on resilient AI calls)
2. Error codes (needed for frontend integration in later sprints)
3. Enhanced AI logging (foundation for observability)
4. Redis rate limiter (big change; needs testing)
5. PyJWT upgrade (safer to do last; lower risk)

### Testing Checklist
- [ ] Circuit breaker retries correctly and fails after max_retries
- [ ] Exponential backoff delays are correct (100ms, 200ms, 400ms, ...)
- [ ] Redis rate limiter enforces limits across multi-process test
- [ ] In-memory rate limiter still works when REDIS_URL not set
- [ ] Old JWT tokens still decode (PyJWT fallback works)
- [ ] New JWT tokens encode/decode correctly with PyJWT
- [ ] All error codes are present and correctly mapped
- [ ] AI logging output is JSON and contains all expected fields
- [ ] No regression: all existing tests pass
- [ ] Rate limit error includes `Retry-After` header

### Deployment Checklist
- [ ] `.env` update: `REDIS_URL` optional (defaults to in-memory if not set)
- [ ] `requirements.txt` updated: `redis>=5.0`, `pyjwt>=2.8.0`
- [ ] `app/core/circuit_breaker.py` created
- [ ] `app/core/rate_limit_redis.py` created
- [ ] `app/core/error_codes.py` created
- [ ] `app/core/telemetry.py` created
- [ ] All AI services updated with telemetry logging
- [ ] `app/core/security.py` updated for PyJWT
- [ ] `docs/ENVIRONMENT.md` updated with REDIS_URL instructions
- [ ] Local test with Docker: `make up && pytest`
- [ ] Staging deployment: verify rate limits work, AI logs present
- [ ] Production deployment: monitor error codes in Sentry
- [ ] Verify no performance regression on /cvs and /jobs endpoints

### Definition of Done
- ✅ Circuit breaker implemented and tested (fails safe after 3 retries)
- ✅ Redis rate limiter functional with in-memory fallback
- ✅ PyJWT integrated with backward compatibility for old tokens
- ✅ Structured error codes in all error responses
- ✅ AI service layer logs all operations with token counts
- ✅ All existing tests pass
- ✅ Production deployment successful; no increase in error rate

---

## **SPRINT 2 — Data Layer & Migrations** (2 weeks)

### Objective
Establish a formal database migration system and optimize query performance with strategic indexing. Prepare the database layer for scaling to thousands of CVs per user.

### Why This Matters
- **Technical**: Runtime schema patching is fragile and unmaintainable; need formal migrations to support schema evolution, multi-environment deployments, and rollbacks
- **Business**: Poor query performance on large datasets (100+ CVs) will degrade user experience; need baseline optimization before feature proliferation
- **Portfolio**: Migrations system + query optimization signals production maturity and database design skills

### Tasks

#### Task 1: Implement Alembic Migration Framework (180 min)
**What**: Set up Alembic as the formal database migration system; create baseline migration for current schema.

**Why**:
- Current: Runtime patching in `app/db/database.py` via SQLAlchemy inspect/create logic
- After: Explicit, versioned migrations that can be reviewed, rollbacked, and replayed

**Details**:
1. Install Alembic in Python: `alembic` to `requirements.txt`

2. Initialize Alembic:
   ```bash
   alembic init app/db/migrations
   ```
   - Creates `app/db/migrations/` with `env.py`, `script.py.mako`, `versions/`

3. Configure `app/db/migrations/env.py`:
   - Set `sqlmodel_metadata = SQLModel.metadata` (Alembic's target_metadata)
   - Enable auto-detection of schema changes: `compare_type=True, compare_server_default=True`

4. Create baseline migration (current schema):
   ```bash
   alembic revision --autogenerate -m "baseline: users, cvs, job_analyses, cv_job_matches"
   ```
   - Review `app/db/migrations/versions/001_baseline.py`
   - Ensure all tables, columns, indexes present
   - Manual fix if needed (Alembic sometimes misses constraints)

5. Mark current databases as migrated:
   - For production: `alembic stamp head` (marks Supabase as up-to-date)
   - For local dev: First run will auto-create if alembic_version table doesn't exist

6. Document:
   - Create `docs/MIGRATIONS.md`:
     - How to create a migration: `alembic revision -m "desc"`
     - How to apply: `alembic upgrade head`
     - How to rollback: `alembic downgrade -1`
     - Preview SQL: `alembic upgrade head --sql`

---

#### Task 2: Add Strategic Database Indexes (120 min)
**What**: Create indexes on commonly-queried columns to improve query performance.

**Why**: 
- Current: Only foreign key and unique indexes; N+1 queries possible; `user_id + created_at DESC` queries are full table scans
- After: Queries on 1000+ CVs will be <100ms instead of >1s

**Details**:
1. Create migration: `alembic revision -m "add performance indexes"`

2. Add indexes:
   ```sql
   -- User-scoped list queries (most common)
   CREATE INDEX idx_cvs_user_id_created_at ON cvs(user_id, created_at DESC);
   CREATE INDEX idx_jobs_user_id_created_at ON job_analyses(user_id, created_at DESC);
   CREATE INDEX idx_matches_user_id_created_at ON cv_job_matches(user_id, created_at DESC);
   
   -- Foreign key lookups
   CREATE INDEX idx_cvs_user_id ON cvs(user_id);
   CREATE INDEX idx_jobs_user_id ON job_analyses(user_id);
   CREATE INDEX idx_matches_user_id ON cv_job_matches(user_id);
   CREATE INDEX idx_matches_cv_id ON cv_job_matches(cv_id);
   CREATE INDEX idx_matches_job_id ON cv_job_matches(job_id);
   
   -- Cover letter lookups
   CREATE INDEX idx_jobs_cover_letter_cv_id ON job_analyses(cover_letter_cv_id);
   
   -- Search/filter (for Sprint 3)
   CREATE INDEX idx_cvs_tags ON cvs USING GIN(tags);  -- PostgreSQL-only; for tag filtering
   ```

3. Measure impact:
   - Before: `SELECT * FROM cvs WHERE user_id = 1 ORDER BY created_at DESC LIMIT 20` → 500ms (1000 rows)
   - After: Same query → <20ms (with index)

4. Test on SQLite + PostgreSQL:
   - SQLite: CREATE INDEX syntax same (no GIN support though)
   - PostgreSQL: EXPLAIN ANALYZE to verify index used

---

#### Task 3: Optimize Queries with Eager Loading (90 min)
**What**: Update SQLModel queries to use `.options(selectinload(...))` to avoid N+1 problems.

**Why**:
- Current: Getting user + all user's CVs = 1 query for user + N queries for each CV (N+1)
- After: One LEFT JOIN query fetches all data in single round-trip

**Details**:
1. Update `app/db/crud.py`:
   - Review all get_user_* functions
   - Replace `.query()` with `.select().options(selectinload(...))` for relationships
   - Example: `select(User).options(selectinload(User.cvs))`

2. Update routes that load user + related data:
   - `GET /auth/me`: user + all CVs/jobs? (check if needed)
   - `GET /cvs`: user + CVs (probably doesn't need full relationship; just list)
   - `GET /jobs`: user + analyses (same; just list)

3. Profile with Django Debug Toolbar equivalent:
   - Add logging: `print(sqlalchemy.event.listen(engine, "before_cursor_execute", print_sql_debug))`
   - Count queries: "SELECT * FROM cvs WHERE user_id = 1" should be 1 query, not N+1

---

#### Task 4: Remove Runtime Schema Patching (60 min)
**What**: Delete ad-hoc schema migration code since Alembic is now source of truth.

**Why**: 
- Current: `app/db/database.py` has `_reset_legacy_dev_tables()`, `_ensure_schema_compatibility()`, etc.
- After: Clean startup; all schema managed via Alembic

**Details**:
1. Update `app/db/database.py`:
   - Remove `_reset_legacy_dev_tables()`
   - Remove `_ensure_job_tracking_columns()`
   - Remove `_ensure_job_cover_letter_columns()`
   - Remove `_ensure_cv_tags_column()`
   - Remove `_ensure_cv_library_summary_column()`
   - Keep only: `create_db_and_tables()` which just calls `SQLModel.metadata.create_all(engine)`
   - Add comment: "Schema is managed by Alembic migrations; see app/db/migrations/"

2. Database startup:
   - Move migration logic: In `app/main.py` lifespan, call `alembic upgrade head` before creating tables
   - Or: In deployment, run `alembic upgrade head` before starting app

3. Test:
   - New fresh database: should auto-create schema via Alembic (or manual run)
   - Old database: should have alembic_version table and be marked as current version

---

#### Task 5: Add Connection Pool Optimization (60 min)
**What**: Configure SQLAlchemy connection pooling to reduce overhead on serverless deployments.

**Why**:
- Current: PostgreSQL uses `NullPool` (no connection reuse); each request opens/closes a connection
- After: `QueuePool` reuses connections within process; reduces latency + cost

**Details**:
1. Update `app/db/database.py`:
   ```python
   from sqlalchemy.pool import QueuePool, NullPool, SingletonThreadPool
   
   if settings.is_postgres:
       # Serverless: NullPool still recommended but can try QueuePool with small size
       # Local dev: QueuePool for connection reuse
       pool_class = QueuePool if not settings.is_production else NullPool
       pool_size = 5 if not settings.is_production else 1
       max_overflow = 10 if not settings.is_production else 0
   else:
       # SQLite: use SingletonThreadPool
       pool_class = SingletonThreadPool
       pool_size = 1
       max_overflow = 0
   
   engine_kwargs = {
       "pool_pre_ping": not settings.is_sqlite,
       "poolclass": pool_class,
       "pool_size": pool_size,
       "max_overflow": max_overflow,
       "pool_recycle": 3600,  # Recycle connections every hour
       "echo": False,  # Set to True for debugging
   }
   ```

2. Test:
   - Measure: repeated `/cvs` calls should reuse connection
   - Monitor: connection count in Supabase dashboard (should stay <5)

3. Document in `docs/DEPLOYMENT.md`:
   - Explain pool settings for serverless vs. traditional deployments
   - Mention Pgbouncer as future optimization (connection pooling proxy)

---

### Dependencies
- Sprint 0 + 1 complete (logging, error handling working)
- Backend running with PostgreSQL or SQLite
- Alembic compatible with SQLModel version
- No active prod deployments during migration setup (or careful rollout)

### Risks
- **Alembic Auto-Detection**: May not catch all schema changes; manual review required on migrations
- **Production Safety**: Can't undo schema changes easily; must test migrations on staging first
- **SQLite Limitations**: Some PostgreSQL-specific features (GIN indexes) won't work on SQLite; need compatibility layer
- **Connection Pool**: Wrong pool settings could cause connection timeouts or leaks

### Implementation Order
1. Alembic setup + baseline migration (creates formal versioning)
2. Remove runtime schema patching (cleans up codebase)
3. Add performance indexes (improves query speed immediately)
4. Optimize queries with eager loading (prevents N+1)
5. Connection pool tuning (reduces overhead)

### Testing Checklist
- [ ] Alembic `alembic upgrade head` runs without errors
- [ ] Baseline migration captures current schema
- [ ] New fresh database: schema created correctly via Alembic
- [ ] Existing production database: alembic_version marked correctly (no duplicate creates)
- [ ] Indexes created: `SELECT * FROM sqlite_master WHERE type='index'` shows new indexes
- [ ] Query performance improved: `SELECT * FROM cvs WHERE user_id = 1 ORDER BY created_at DESC LIMIT 20` <50ms
- [ ] Eager loading works: no N+1 queries observed in logs
- [ ] Connection pool reuses connections (monitor pool size in logs)
- [ ] All existing tests pass
- [ ] SQLite and PostgreSQL both work

### Deployment Checklist
- [ ] `requirements.txt` updated with `alembic`
- [ ] `app/db/migrations/env.py` configured for SQLModel
- [ ] Baseline migration created: `app/db/migrations/versions/001_baseline.py`
- [ ] `docs/MIGRATIONS.md` created
- [ ] Runtime schema patching code removed from `app/db/database.py`
- [ ] Production database stamped: `alembic stamp head`
- [ ] Connection pool settings tested locally
- [ ] Staging deployment: `alembic upgrade head` runs before app start
- [ ] Production deployment: same as staging
- [ ] Monitor query performance baseline

### Definition of Done
- ✅ Alembic initialized and baseline migration in version control
- ✅ Runtime schema patching removed (code cleanup)
- ✅ Performance indexes created + tested
- ✅ Eager loading implemented for common queries
- ✅ Connection pool configured appropriately
- ✅ Query performance measured and baselined
- ✅ All tests pass
- ✅ Production deployment successful; no performance regression

---

## **SPRINT 3 — API Improvements & Scaling** (2 weeks)

### Objective
Prepare the backend API for handling thousands of CVs per user. Add pagination, filtering, and search capabilities. Refactor error handling to be more consistent.

### Why This Matters
- **Technical**: Without pagination, `GET /cvs` response grows linearly with user data; slow and expensive at scale
- **Business**: Users with 100+ CVs will have poor experience; API becomes a bottleneck
- **Portfolio**: Pagination + filtering shows understanding of server-side data handling and API design

### Tasks

#### Task 1: Implement Pagination Framework (120 min)
**What**: Create a reusable pagination system for all list endpoints.

**Details**:
1. Create `app/core/pagination.py`:
   ```python
   from pydantic import BaseModel, Field
   from typing import Generic, TypeVar, List
   
   T = TypeVar('T')
   
   class PaginationParams(BaseModel):
       limit: int = Field(default=20, ge=1, le=100)
       offset: int = Field(default=0, ge=0)
   
   class PaginatedResponse(BaseModel, Generic[T]):
       items: List[T]
       pagination: dict
       
   def paginate_query(session, query, limit: int, offset: int, total_count: int):
       """Helper to apply limit+offset to SQLModel query"""
       items = query.offset(offset).limit(limit).all()
       return {
           "items": items,
           "pagination": {
               "total": total_count,
               "limit": limit,
               "offset": offset,
               "has_more": offset + limit < total_count
           }
       }
   ```

2. Update `GET /cvs` endpoint:
   - Add query params: `limit`, `offset`
   - Return paginated response: `{ items: [...], pagination: { total, limit, offset, has_more } }`
   - Test: `GET /cvs?limit=10&offset=0` → 10 CVs + pagination info

3. Same for `GET /jobs` and `GET /matches`

---

#### Task 2: Add Filtering & Search (120 min)
**What**: Allow users to search CVs by display_name and filter by tags.

**Details**:
1. Update `GET /cvs` endpoint:
   - Add `?search=<text>` → filter by display_name (case-insensitive substring match)
   - Add `?tags=<tag1>&tags=<tag2>` → filter by tags (any tag match = include)
   - Combine filters: e.g., `GET /cvs?search=backend&tags=python&limit=20`

2. Implement search/filter in CRUD:
   ```python
   def get_user_cvs_filtered(session, user_id, search: str = "", tags: list = None, limit: int = 20, offset: int = 0):
       query = select(CV).where(CV.user_id == user_id)
       
       if search:
           query = query.where(CV.display_name.ilike(f"%{search}%"))
       
       if tags:
           # CV has tags array; filter if CV contains ANY of the requested tags
           from sqlalchemy import or_
           conditions = [CV.tags.contains([tag]) for tag in tags]
           query = query.where(or_(*conditions))
       
       total = session.exec(query.select()).count()
       items = session.exec(query.limit(limit).offset(offset)).all()
       return items, total
   ```

3. Test: `GET /cvs?search=resume&tags=python,backend` → returns matching CVs

---

#### Task 3: Add Bulk Operations Endpoints (90 min)
**What**: Allow users to delete multiple CVs or tag multiple CVs at once.

**Details**:
1. Create `POST /cvs/bulk-delete`:
   - Request: `{ cv_ids: [1, 2, 3] }`
   - Response: `{ deleted: 3, failed: 0 }`
   - Verify user owns all CVs before deleting

2. Create `POST /cvs/bulk-tag`:
   - Request: `{ cv_ids: [1, 2], tags: ["python", "backend"] }`
   - Response: `{ updated: 2, failed: 0 }`
   - Append tags to existing tags (merge)

3. Test: Bulk delete 5 CVs; verify they're gone

---

#### Task 4: Standardize API Error Responses (60 min)
**What**: Ensure all error responses follow a consistent schema.

**Details**:
1. Standard error response format:
   ```json
   {
     "error": {
       "code": "ERR_CV_NOT_FOUND",
       "message": "CV with ID 999 not found",
       "request_id": "trace-id-uuid",
       "timestamp": "2026-04-02T12:00:00Z"
     }
   }
   ```

2. Update all error responses to include this format

3. Test: All error scenarios return correct format

---

#### Task 5: Add API Request/Response Size Limits (60 min)
**What**: Enforce request/response size limits to prevent abuse or runaway costs.

**Details**:
1. Middleware to check request body size:
   - Max: 10MB (for file uploads)
   - Return 413 Payload Too Large if exceeded

2. Response size warning:
   - Log if response > 5MB (unusual for list endpoints; signals problem query)

3. Test: Upload >10MB file → 413

---

### Dependencies
- Sprint 0–2 complete
- Database with performance indexes (from Sprint 2)
- Error handling framework (from Sprint 1)

### Risks
- **Tag Filtering Complexity**: PostgreSQL/SQLite syntax different for array/JSON filtering; need careful SQL
- **Performance on Large Datasets**: Complex filter queries may be slow; need query optimization
- **Backward Compat**: Existing frontend expecting flat list; may break if response format changes (add `compat` mode?)

### Implementation Order
1. Pagination framework (foundation for all list endpoints)
2. Search/filter (builds on pagination)
3. Bulk operations (independent)
4. Standardize errors (small clean-up)
5. Request/response size limits (safety)

### Testing Checklist
- [ ] Pagination works: `GET /cvs?limit=10&offset=0` returns 10 items + pagination info
- [ ] Search works: `GET /cvs?search=resume` returns matching CVs
- [ ] Tag filtering works: `GET /cvs?tags=python&tags=backend` returns CVs with any of those tags
- [ ] Bulk delete: `POST /cvs/bulk-delete` deletes multiple CVs
- [ ] Bulk tag: `POST /cvs/bulk-tag` appends tags to multiple CVs
- [ ] Error responses include error code + trace ID
- [ ] Request size limit enforced: 413 on >10MB
- [ ] All existing tests pass

### Deployment Checklist
- [ ] `app/core/pagination.py` created
- [ ] Pagination added to `/cvs`, `/jobs`, `/matches`
- [ ] Search/filter query logic added to CRUD
- [ ] New bulk endpoints added
- [ ] Error response format consistent
- [ ] Size limits enforced in middleware
- [ ] Frontend updated to handle new pagination format (can be compat mode)
- [ ] Local testing: make up && pytest
- [ ] Staging deployment: verify pagination works on large dataset
- [ ] Production deployment: monitor request patterns

### Definition of Done
- ✅ All list endpoints support pagination
- ✅ Search and filtering working on CVs
- ✅ Bulk operations implemented
- ✅ Error responses standardized with error codes
- ✅ Request/response size limits enforced
- ✅ Performance tested on 1000+ CVs
- ✅ All tests pass

---

## **SPRINT 4 — Frontend Polish & UX** (2 weeks)

### Objective
Improve frontend user experience, fix visual bugs, add loading states and better error handling. Prepare for production mobile viewing.

### Why This Matters
- **Technical**: Async operations need user feedback (loading spinners); errors need clear messaging
- **Business**: Poor UX = high churn; users give up if app feels unresponsive
- **Portfolio**: Frontend polish signals attention to detail and product thinking

### Tasks

#### Task 1: Fix Frontend Encoding Mojibake (if not done in Sprint 0) (30 min)
**What**: Remove garbled Unicode characters from UI strings.

---

#### Task 2: Add Dark Mode Support (120 min)
**What**: Detect system dark mode preference; add UI toggle to switch.

**Details**:
1. Update `frontend/src/context/AppThemeContext.tsx`:
   - Default: `prefers-color-scheme: dark` → dark mode; else light mode
   - Persist choice to localStorage
   - Expose toggle: `toggleDarkMode()`

2. Update Tailwind config to support dark mode:
   ```js
   module.exports = {
     darkMode: 'class',  // Use class-based dark mode
     // ... rest of config
   }
   ```

3. Update all pages to use `dark:bg-slate-900 dark:text-white` Tailwind classes

4. Add toggle button in navbar:
   - Icon: sun/moon toggle
   - On click: call `toggleDarkMode()`

5. Test: Toggle dark mode; all pages render correctly

---

#### Task 3: Add Loading Skeletons on Async Operations (120 min)
**What**: Show skeleton loaders while waiting for AI operations.

**Details**:
1. Create `frontend/src/components/SkeletonLoader.tsx`:
   - Generic skeleton component using shimmer animation
   - Used for CV lists, job analysis, match results

2. Update pages:
   - `JobAnalysisPage`: Show skeleton while analyzing (currently blank screen)
   - `MatchesPage`: Show skeleton while loading matches
   - `CVLibraryPage`: Show skeleton while uploading CVs

3. CSS: Shimmer animation (pulse effect):
   ```css
   @keyframes shimmer {
     0% { background-position: -1000px 0; }
     100% { background-position: 1000px 0; }
   }
   ```

---

#### Task 4: Improve Error Handling & Toast Messages (120 min)
**What**: Show user-friendly error toasts instead of silent failures or browser alerts.

**Details**:
1. Create `frontend/src/components/Toast.tsx`:
   - Component: toast notifications (bottom-right by default)
   - Types: success, error, warning, info
   - Auto-dismiss after 5s

2. Create `frontend/src/context/ToastContext.tsx`:
   - Global toast state + methods
   - `showToast(message, type, duration)`

3. Update pages:
   - On API error: `showToast(error.message, 'error')`
   - On success: `showToast('CV uploaded!', 'success')`

4. Update `frontend/src/services/api.ts`:
   - Parse error.response.error.code
   - Map to user-friendly message:
     - "ERR_RATE_LIMIT" → "You're making requests too quickly. Please wait a moment."
     - "ERR_AI_TIMEOUT" → "Analysis took too long. Please try again."
     - "ERR_CV_NOT_FOUND" → "CV not found. It may have been deleted."

---

#### Task 5: Add Responsive Design Improvements (90 min)
**What**: Ensure UI works well on mobile (375px), tablet (768px), and desktop (1440px).

**Details**:
1. Test on multiple viewport sizes
2. Fix component layouts:
   - Stack columns on mobile
   - Two-column on tablet
   - Multi-column on desktop

3. Use Tailwind responsive classes: `md:`, `lg:`, `2xl:`

4. Test: Open each page on iOS/Android emulator; no overflow or truncation

---

#### Task 6: Implement Form Input Validation (60 min)
**What**: Validate forms before submission; show clear error messages.

**Details**:
1. Use Zod or simple validation library
2. Validate on blur + onChange for immediate feedback
3. Show error messages below each input
4. Test: Invalid email format → error message appears

---

### Dependencies
- Sprint 0–3 complete
- Frontend environment variables configured
- Tailwind CSS configured

### Risks
- **Dark Mode Flashing**: If dark mode not detected early, page may flash light before switching; fix with CSS in `<head>`
- **Skeleton Performance**: Overly complex skeletons may perform poorly
- **Toast Stacking**: Multiple errors may create toast stack; limit to 3 simultaneous

### Implementation Order
1. Dark mode (foundational; affects all pages)
2. Loading skeletons (improves UX of slow operations)
3. Error handling + toasts (completes error UX)
4. Responsive design (ensures mobile UX)
5. Form validation (polish)

### Testing Checklist
- [ ] Dark mode toggle works; preference persists across page reloads
- [ ] All pages render in both light + dark mode without glitches
- [ ] Skeleton loaders appear while waiting for API responses
- [ ] Toast notifications appear on success/error
- [ ] Error messages are user-friendly (not raw error codes)
- [ ] Mobile responsive: 375px width shows readable layout
- [ ] Form validation prevents invalid submissions
- [ ] All existing tests pass

### Deployment Checklist
- [ ] `AppThemeContext` created + integrated
- [ ] Dark mode CSS in Tailwind
- [ ] `SkeletonLoader` component created
- [ ] `Toast` + `ToastContext` created
- [ ] Error handling updated in all API calls
- [ ] Responsive classes added to key components
- [ ] Form validation library (zod) added to package.json
- [ ] Local testing: npm run dev; test on mobile emulator
- [ ] Build check: npm run build (no errors)
- [ ] Staging deployment
- [ ] Production deployment

### Definition of Done
- ✅ Dark mode working with persistent preference
- ✅ Loading skeletons on all async operations
- ✅ Toast messages for all errors
- ✅ Responsive design on mobile (375px), tablet (768px), desktop (1440px)
- ✅ Form validation working
- ✅ No encoding mojibake in UI
- ✅ All tests pass

---

## **SPRINT 5 — Quick-Win Features** (1 week)

### Objective
Ship small, high-value features that improve user experience without requiring architectural changes.

### Why This Matters
- **Business**: Quick wins maintain momentum and show progress
- **Users**: Small features can have disproportionate delight factor
- **Team**: Morale booster; sees tangible impact fast

### Tasks

#### Task 1: Job Saved List (Bookmark) (120 min)
**What**: Allow users to bookmark jobs without analyzing them (research later).

**Details**:
1. Backend:
   - Add `is_saved: bool = False` to `JobAnalysis` model
   - Create `PATCH /jobs/{job_id}/toggle-saved`: toggle bookmark flag
   - List endpoint: `GET /jobs?saved=true` to show bookmarks

2. Frontend:
   - Add bookmark icon (filled/unfilled) on job card
   - On click: toggle saved status
   - Filter dropdown: "Show All", "Saved Only", "Analyzed Only"

3. Test: Bookmark a job; refresh page; bookmark persists

---

#### Task 2: CV Favorites (Pin/Star) (90 min)
**What**: Users can mark 2–3 CVs as favorites for quick access.

**Details**:
1. Backend:
   - Add `is_favorite: bool = False` to `CV` model
   - Create `PATCH /cvs/{cv_id}/toggle-favorite`

2. Frontend:
   - Star icon on CV card
   - On click: toggle favorite
   - Sort CVs: favorites first

3. Test: Mark CV as favorite; appears at top of list

---

#### Task 3: Rate Limit Tuning (Production) (15 min)
**What**: Increase cover letter rate limit based on data.

**Details**:
1. Analyze: How many users hit cover letter limit?
2. If <5%: increase from 4 to 6/hour
3. If >15%: decrease from 4 to 3/hour + add upsell messaging
4. Update `ENV_DEFAULTS["production"]`

---

#### Task 4: Copy-to-Clipboard Actions (60 min)
**What**: Let users copy cover letters, match summaries to clipboard for sharing.

**Details**:
1. Add copy button next to generated text
2. On click: copy to clipboard; show "Copied!" toast
3. Use `navigator.clipboard.writeText()`

---

### Dependencies
- All previous sprints complete

### Risks
- None major; small features with low risk

### Testing Checklist
- [ ] Bookmark job; persists after refresh
- [ ] Mark CV favorite; appears at top of list
- [ ] Copy to clipboard works on all text outputs
- [ ] All existing tests pass

### Deployment Checklist
- [ ] Database migration: add is_saved, is_favorite columns
- [ ] New endpoints: toggle-saved, toggle-favorite
- [ ] Frontend components updated
- [ ] Production rate limits updated
- [ ] Local testing: make up && pytest
- [ ] Staging deployment
- [ ] Production deployment

### Definition of Done
- ✅ Job bookmarks working
- ✅ CV favorites working
- ✅ Copy-to-clipboard working
- ✅ Rate limits tuned
- ✅ All tests pass

---

## **SPRINT 6 — Reliability & Testing** (2 weeks)

### Objective
Build comprehensive test suite and monitoring to ensure production reliability. Target 70% code coverage.

### Why This Matters
- **Technical**: Confidence in deployments; catch regressions early
- **Portfolio**: Test-driven development signals software engineering maturity
- **Business**: Reduces bugs and incident response time

### Tasks

#### Task 1: Comprehensive Test Suite (240 min)
**What**: Add integration tests for all major workflows.

**Details**:
1. Test Coverage Targets:
   - Backend services: 70% (job_analyzer, cv_analyzer, cover_letter_service)
   - Routes: 80% (auth, cvs, jobs)
   - Core: 90% (security, error_codes, pagination)

2. Test Categories:

   **Auth Tests** (TestAuth):
   - [ ] Register new user → success
   - [ ] Register duplicate email → error
   - [ ] Login with correct password → returns token
   - [ ] Login with incorrect password → 401
   - [ ] Token expires → 401
   - [ ] Rate limited on too many login attempts → 429

   **CV Upload Tests** (TestCVUpload):
   - [ ] Upload valid PDF → success, summary generated
   - [ ] Upload duplicate CV → detected, skipped or merged
   - [ ] Upload oversized PDF → 413 error
   - [ ] Upload non-PDF → error
   - [ ] Batch upload 5 CVs → all succeed
   - [ ] Batch upload with 1 invalid → others succeed

   **Job Analysis Tests** (TestJobAnalysis):
   - [ ] Analyze valid job → success, structured output
   - [ ] Analyze oversized job → truncated gracefully
   - [ ] Analyze while rate limited → 429
   - [ ] Analyze fails (AI timeout) → circuit breaker triggered, error returned

   **CV Matching Tests** (TestCVMatching):
   - [ ] Match valid CV to job → success, fit score returned
   - [ ] Match deleted CV → 404
   - [ ] Match job from another user's CV → forbidden
   - [ ] Compare two CVs against job → winner selected deterministically

   **Cover Letter Tests** (TestCoverLetter):
   - [ ] Generate cover letter → success
   - [ ] Generate while rate limited → 429
   - [ ] Regenerate cover letter → overwrites previous

   **Pagination Tests** (TestPagination):
   - [ ] Get first page of CVs → 20 items
   - [ ] Get second page → different items, has_more=true
   - [ ] Search filters results correctly
   - [ ] Tag filter works

3. Write tests using pytest + fixtures:
   ```python
   @pytest.fixture
   def authenticated_user(client):
       # Register + login; return token
       pass
   
   def test_upload_cv(authenticated_user):
       # Use authenticated_user token to upload
       pass
   ```

---

#### Task 2: Performance Benchmarks (120 min)
**What**: Establish baseline latencies for critical operations; alert if degraded.

**Details**:
1. Measure endpoints:
   - `/health`: <50ms
   - `/auth/login`: <300ms
   - `/cvs`: <200ms (100 CVs in DB)
   - `/jobs/{id}/match-cvs`: <5s (AI operation)
   - `POST /cvs/batch-upload`: <15s (5 x 1MB PDFs)

2. Create benchmark script:
   ```python
   # tests/benchmark.py
   import time
   def test_benchmark_list_cvs(client, authenticated_user):
       times = []
       for _ in range(10):
           start = time.time()
           response = client.get("/cvs", headers={"Authorization": f"Bearer {authenticated_user}"})
           times.append((time.time() - start) * 1000)
       avg = sum(times) / len(times)
       assert avg < 200, f"Average latency too high: {avg}ms"
   ```

3. Run on staging + record baseline

---

#### Task 3: Frontend Component Tests (90 min)
**What**: Add unit tests for React components (optional but good practice).

**Details**:
1. Test key components:
   - `LoginPage`: form validation, submission
   - `CVLibraryPage`: upload, list, delete
   - `JobAnalysisPage`: input validation, loading state
   - `Toast`: message display, auto-dismiss

2. Use Jest + React Testing Library:
   ```bash
   npm install --save-dev jest @testing-library/react @testing-library/jest-dom
   ```

3. Example test:
   ```javascript
   test('LoginPage shows error on invalid email', () => {
       render(<LoginPage />);
       fireEvent.change(screen.getByLabelText('Email'), {
           target: { value: 'invalid' }
       });
       fireEvent.click(screen.getByText('Login'));
       expect(screen.getByText('Invalid email format')).toBeInTheDocument();
   });
   ```

---

#### Task 4: Monitoring & Alerting Setup (120 min)
**What**: Configure dashboards and alerts for production health.

**Details**:
1. Metrics to track:
   - Error rate (% of requests returning 5xx)
   - API latency (p50, p95, p99)
   - Token usage (cumulative spend)
   - Rate limit hits
   - Circuit breaker trips

2. Sentry configuration:
   - Set up alerts: >10 errors/min → Slack notification
   - Group errors by type
   - Track release health

3. Vercel monitoring:
   - Monitor build times
   - Check response times per endpoint
   - View cold start latency

4. Optional: Create simple dashboard
   ```json
   {
     "metrics": {
       "error_rate": "0.5%",
       "p95_latency": "200ms",
       "token_spend_today": "$1.23"
     }
   }
   ```

---

### Dependencies
- All previous sprints complete
- Testing infrastructure in place
- Sentry account configured

### Risks
- **Test Maintenance**: Tests can be fragile; need to update with code changes
- **Coverage Gaming**: 70% coverage doesn't mean quality; focus on critical paths
- **Performance Variance**: Latency benchmarks vary; use ranges not exact numbers

### Implementation Order
1. Core test suite (auth, uploads, analysis) - highest value
2. Integration tests (end-to-end workflows)
3. Performance benchmarks
4. Frontend component tests (optional)
5. Monitoring setup

### Testing Checklist
- [ ] 70% code coverage achieved (measured by pytest-cov)
- [ ] All critical workflows tested (auth, upload, analyze, match, cover letter)
- [ ] Latency benchmarks established + pass
- [ ] Regression tests prevent future regressions
- [ ] Frontend tests pass (if implemented)
- [ ] Sentry alerts configured
- [ ] Monitoring dashboard functional

### Deployment Checklist
- [ ] Test suite runs in CI/CD (GitHub Actions or similar)
- [ ] Coverage reports generated + visible
- [ ] Benchmarks run on staging environment
- [ ] Performance baselines documented
- [ ] Sentry project configured + alerts set
- [ ] Monitoring dashboard accessible to team
- [ ] Pre-deploy: run full test suite (must pass before merge)

### Definition of Done
- ✅ 70% code coverage (measured)
- ✅ All critical workflows tested
- ✅ Performance benchmarks established
- ✅ Monitoring + alerting configured
- ✅ Confidence to deploy safely

---

## **SPRINT 7 — Advanced Features (Monetization Ready)** (2 weeks)

### Objective
Implement infrastructure for SaaS monetization. Add usage tracking, freemium tier support, and subscription features.

### Why This Matters
- **Business**: Enable revenue generation and sustainable growth
- **Product**: Freemium tier validates willingness to pay
- **Technical**: Subscription logic is foundation for future premium features

### Tasks

#### Task 1: Create User Subscription Tier Model (90 min)
**What**: Add subscription support to User model; implement tier-based feature gating.

**Details**:
1. Backend migration:
   - Add columns to User: `subscription_tier: str = "free"`, `subscription_expires_at: datetime | None`
   - Values: "free", "pro", "enterprise"

2. Create `app/core/subscriptions.py`:
   ```python
   class SubscriptionTier(str, Enum):
       FREE = "free"
       PRO = "pro"
       ENTERPRISE = "enterprise"
   
   TIER_FEATURES = {
       "free": {
           "max_cvs": 5,
           "max_analyses": 10,
           "max_cover_letters": 2,
       },
       "pro": {
           "max_cvs": 100,  # unlimited in UI
           "max_analyses": 500,
           "max_cover_letters": 100,
       },
       "enterprise": {
           "max_cvs": 10000,
           "max_analyses": 10000,
           "max_cover_letters": 10000,
       }
   }
   
   def check_feature_access(user: User, feature: str) -> bool:
       tier_features = TIER_FEATURES[user.subscription_tier]
       # Check against usage_today or similar tracking
       return True  # or False if limit exceeded
   ```

3. Create `@require_tier("pro")` decorator:
   ```python
   def require_tier(tier: str):
       async def decorator(request: Request, call_next):
           user = request.user
           if user.subscription_tier not in [tier, "enterprise"]:
               raise HTTPException(status_code=403, detail="Feature requires Pro tier")
           return await call_next(request)
       return decorator
   ```

---

#### Task 2: Usage Tracking & Dashboard (150 min)
**What**: Track user's API usage (CVs uploaded, analyses run, cover letters generated) per tier limits.

**Details**:
1. Create `UsageTracking` table:
   - `user_id`, `operation` (upload_cv, analyze_job, generate_cover_letter), `date`, `count`
   - Reset counts daily

2. Update endpoints:
   - Before CV upload: check `today_uploads < max_cvs` for tier
   - Before job analysis: check `today_analyses < max_analyses` for tier
   - Before cover letter: check `today_cover_letters < max_cover_letters` for tier

3. Create `GET /usage` endpoint:
   ```json
   {
     "tier": "free",
     "usage": {
       "cvs_today": 3,
       "cvs_limit": 5,
       "analyses_today": 8,
       "analyses_limit": 10,
       "cover_letters_today": 1,
       "cover_letters_limit": 2
     }
   }
   ```

4. Frontend `UsageDashboard` component:
   - Show progress bars for each quota
   - Display "Upgrade to Pro" button if near limit

---

#### Task 3: Stripe Integration (Mock) (120 min)
**What**: Prepare Stripe integration for payment processing (full implementation in future sprint).

**Details**:
1. Add `stripe` library to requirements.txt

2. Create `app/core/payments.py`:
   ```python
   import stripe
   
   stripe.api_key = os.getenv("STRIPE_API_KEY")
   
   def create_checkout_session(user_id: str, tier: str = "pro"):
       """Create Stripe checkout link for subscription"""
       # Prices configured in Stripe dashboard
       price_ids = {
           "pro": "price_1xxx",
           "enterprise": "price_2xxx"
       }
       session = stripe.checkout.Session.create(
           payment_method_types=["card"],
           line_items=[{
               "price": price_ids[tier],
               "quantity": 1,
           }],
           mode="subscription",
           success_url="https://jobpi.app/success",
           cancel_url="https://jobpi.app/settings",
           client_reference_id=user_id,
       )
       return session.url
   ```

3. Create `POST /billing/checkout` endpoint:
   - Returns Stripe checkout URL
   - Frontend redirects user to Stripe

4. Webhook handler for `invoice.payment_succeeded`:
   - Update user tier to "pro"
   - Set `subscription_expires_at`

5. Test: Can generate Stripe checkout link (no actual payment in dev)

---

#### Task 4: Email Notification Infrastructure (90 min)
**What**: Set up email sending for notifications, digests, and usage alerts.

**Details**:
1. Add email service: SendGrid or AWS SES (mock for now)

2. Create `app/services/email_service.py`:
   ```python
   def send_usage_alert(user_email: str, tier: str, usage: dict):
       """Send email if user near quota limit"""
       subject = "You're running out of analyses this month!"
       template = f"Hey {user_email}, you've used {usage['analyses_today']}/{usage['analyses_limit']} analyses..."
       # send_email(user_email, subject, template)
   
   def send_weekly_digest(user_email: str, stats: dict):
       """Send weekly summary email"""
       pass
   ```

3. Cron job (future sprint): Run daily to send alerts

---

#### Task 5: Freemium Tier Gating (120 min)
**What**: Enforce tier limits on endpoints; return upsell messaging when limits hit.

**Details**:
1. Update endpoints:
   - `POST /cvs/upload`: if free tier + already 5 CVs → return 403 with upsell
   - `POST /cvs/batch-upload`: same check per file
   - `POST /jobs/{id}/cover-letter`: check cover letter limit
   - `POST /jobs/analyze`: check analysis limit

2. Response body on limit hit:
   ```json
   {
     "error": "Free tier limit reached",
     "code": "ERR_TIER_LIMIT",
     "upgrade_url": "https://jobpi.app/billing/subscribe/pro",
     "next_reset": "2026-04-03T00:00:00Z"
   }
   ```

3. Frontend: Show upgrade modal with CTA

---

### Dependencies
- All previous sprints complete
- Stripe dashboard set up (if real payments)
- Email service account (SendGrid, AWS SES)

### Risks
- **Payment Processing**: Stripe integration must be carefully tested; financial transactions risky
- **Free Tier UX**: Hitting limits frustrates users; ensure UX clearly explains path to upgrade
- **Account Migration**: Existing users must be assigned tier (default: free)

### Implementation Order
1. User tier model + gating (foundation)
2. Usage tracking + dashboard (visibility)
3. Tier enforcement on endpoints (enforcement)
4. Email notifications (optional but valuable)
5. Stripe integration (payment processing)

### Testing Checklist
- [ ] Free tier user hits CV limit → 403 returned with upgrade message
- [ ] Pro tier user can upload unlimited CVs
- [ ] Usage dashboard shows correct counts
- [ ] Email alert sent when user near limit
- [ ] Stripe checkout link generates (mock or test mode)
- [ ] User tier updates on successful payment (webhook test)
- [ ] All existing tests pass (with tier mocking)

### Deployment Checklist
- [ ] Database migration: add subscription columns to User
- [ ] Tier constants + feature mapping defined
- [ ] Endpoints gated by tier (@require_tier decorator)
- [ ] Usage tracking logged + persisted
- [ ] Stripe API credentials configured (env vars)
- [ ] Email service credentials configured (env vars)
- [ ] Frontend upgrade modal created
- [ ] Usage dashboard endpoint + component created
- [ ] Existing users assigned to "free" tier
- [ ] Staging deployment + full workflow test (register → hit limit → upgrade modal)
- [ ] Production deployment

### Definition of Done
- ✅ User tier model implemented
- ✅ Usage limits enforced by tier
- ✅ Usage dashboard functional
- ✅ Tier gating works (free tier users see limits)
- ✅ Email notifications working
- ✅ Stripe integration ready (checkout flow works)
- ✅ All tests pass
- ✅ Ready for paid customer onboarding

---

# Final Guidance

## Quickest Sprint to Execute First
**Sprint 0 — Foundation & Observability** (1 week)
- Lowest complexity
- No architecture changes
- Quick wins build momentum
- Sets up infrastructure for all future sprints

## Highest Impact Sprint
**Sprint 1 — Critical Backend Fixes** (2 weeks)
- Unblocks production scaling
- Fixes security risk (JWT)
- Establishes error handling foundation
- Everything depends on this

## Safest Order for Iterative Deploys
1. **Sprint 0** → Deploy (observation + quick wins)
2. **Sprint 1** → Deploy (backend resilience)
3. **Sprint 2** → Deploy (data layer safety)
4. **Sprint 3** → Deploy (API scalability)
5. **Sprint 4** → Deploy (UX polish)
6. **Sprint 5** → Deploy (feature delight)
7. **Sprint 6** → Deploy (testing + confidence)
8. **Sprint 7** → Deploy (monetization)

## Recommended Next Sprint to Start Right Now
**Start Sprint 0 this week** (4 days of work):
1. Day 1: Fix encoding mojibake + JSON logging
2. Day 2: Sentry integration + rate limit audit
3. Day 3: Health check documentation + testing
4. Day 4: Deployment + monitoring

**Then immediately begin Sprint 1** (can be done in parallel by 2nd engineer):
- Day 1–2: Circuit breaker + error codes
- Day 3–4: Redis rate limiter research + setup
- Day 5: PyJWT upgrade + testing

---

**END OF SPRINT ROADMAP**

This roadmap leaves nothing to chance. Every sprint is deployable, testable, and builds on solid foundations. Each sprint includes specific Codex prompts for planning, implementation, testing, and deployment verification.

**Execution starts Monday. Good luck!**
