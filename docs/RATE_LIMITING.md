# Rate Limiting

JOBPI now chooses its rate-limiter backend at runtime:

- If `REDIS_URL` is set, the API uses a Redis-backed limiter for shared counters across instances.
- If `REDIS_URL` is not set, the API uses the in-memory limiter.
- If Redis is configured but temporarily unavailable, the limiter falls back to the in-memory implementation so the app stays available.

## Current Policies

| Policy | Development | Production | Notes |
| --- | --- | --- | --- |
| Auth register | 20 requests / 300 seconds | 3 requests / 600 seconds | Applied before duplicate-account checks |
| Auth login | 30 requests / 300 seconds | 5 requests / 600 seconds | Uses the request subject or client IP |
| Job analysis | 30 requests / 300 seconds | 6 requests / 3600 seconds | Protects AI analysis spend |
| Match CVs | 30 requests / 300 seconds | 8 requests / 3600 seconds | Covers fit-analysis requests |
| Cover letter | 6 requests / 600 seconds | 4 requests / 3600 seconds | Development is intentionally looser for iteration |
| CV upload | 20 requests / 300 seconds | 5 requests / 3600 seconds | Applies to upload endpoints |

## Implementation Notes

- The in-memory limiter stores event timestamps in a per-process deque.
- The Redis limiter stores counters under `ratelimit:{policy_name}:{subject}` with key expiry equal to the policy window.
- Authenticated users are bucketed by `user:{id}`.
- Anonymous requests fall back to `x-forwarded-for`, then the request client IP.
- When a limit is exceeded, the API returns HTTP `429` and a `Retry-After` header.
- One trusted email can bypass user limits via `TRUSTED_USER_EMAIL`.

## Operational Caveat

The in-memory backend is still safe for local development, but only the Redis backend provides shared enforcement across horizontally scaled instances. Production should set `REDIS_URL` to avoid per-instance drift.
