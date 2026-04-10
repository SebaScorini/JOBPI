# Test Suite

This directory contains the backend pytest suite and a small benchmark smoke script.

## What Lives Here

- `conftest.py`: shared fixtures and test helpers
- `test_*.py`: backend unit and integration-style tests
- `benchmark.py`: local benchmark smoke script used in CI as a lightweight regression check

## Running the Backend Tests

The pytest suite does not require a separately running API server. It imports the application directly.

```bash
pytest -q
pytest --cov=app --cov-report=term-missing -q
```

To run a single file or test:

```bash
pytest tests/test_job_delete.py -q
pytest tests/test_job_delete.py::test_delete_job_removes_owned_job_only -q
```

## Running Through Docker

If you are already using the Docker stack, you can run pytest inside the backend container:

```bash
make test
```

## Frontend Checks

Frontend tests live in `frontend/` and are run separately:

```bash
cd frontend
npm run test
npm run build
```

## Notes

- Pytest configuration lives in the root `pytest.ini`.
- Local temporary cache directories may appear during test runs; they are reproducible artifacts and not part of the source tree.
