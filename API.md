# API

The canonical API contract lives in [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md).

Quick notes:

- Base resources: `/auth`, `/cvs`, `/jobs`, `/matches`, `/health`.
- Bearer authentication is required for all endpoints except register, login, and health.
- Error payloads use a structured envelope with code, message, request_id, and timestamp.

See also:

- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)
- [`README.md`](README.md)