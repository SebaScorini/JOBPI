# Health Check

Use this checklist after each deployment to confirm JOBPI is healthy and observable.

## Sprint 7 Local Reliability Checks

Before deployment, run:

```powershell
pytest -q
pytest --cov=app --cov-report=term-missing -q
python tests/benchmark.py
cd frontend
npm run test
npm run build
```

Record the printed benchmark timings so you can compare future changes against the same local baseline.

## Core API

1. Verify the health endpoint responds successfully.

   ```bash
   curl https://jobpi-api.vercel.app/health
   ```

   Expected result: HTTP `200` with `{"status":"ok"}`.

2. Confirm request logs are emitted in JSON and include `trace_id`.

## Authentication

1. Register a test user or log in with an existing account.
2. Call `GET /auth/me` with a bearer token.
3. Confirm successful authenticated requests return `200`.
4. Confirm invalid credentials still return the expected `401` or `403`.
5. Confirm AI timeout responses, when triggered, return the standardized `ERR_AI_TIMEOUT` code.

## Database-Backed Flows

1. Create or list CV records.
2. Create or list saved job analyses.
3. Confirm data can still be written and read without schema issues.

## AI Flows

1. Submit a representative job analysis request.
2. Run a CV match request.
3. Generate one cover letter if AI credentials are configured.
4. Confirm responses succeed or fail gracefully without timeouts or malformed payloads.

## Rate Limiting

1. Enable rate limiting in the target environment if it is disabled locally.
2. Repeatedly hit one protected route until it returns `429`.
3. Confirm the response includes `Retry-After`.

## Logging And Error Tracking

1. Confirm normal requests produce `request_start` and `request_end` JSON logs.
2. Confirm the same request carries a consistent `trace_id`.
3. If `SENTRY_DSN` is configured, trigger one controlled server error and verify it appears in Sentry with request path, method, and trace metadata.
4. Confirm expected client-side failures such as auth or validation issues do not create noisy server-error alerts.
