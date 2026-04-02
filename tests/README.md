# Test Suite

All tests for JOBPI are organized in this directory.

## Test Files

- `test_improvements.py` - Validates email, password, pagination improvements and API health
- `test_cv_summary_isolation.py` - CV summary isolation tests  
- `test_dspy_configure.py` - DSPy configuration tests
- `test_job_delete.py` - Job deletion tests

## Running Tests

### Run all tests
```bash
# Using pytest
pytest

# Using make
make test

# Using Docker
make bash
pytest
```

### Run specific test file
```bash
pytest tests/test_improvements.py -v
```

### Run specific test function
```bash
pytest tests/test_improvements.py::test_email_validation -v
```

### Run with coverage
```bash
pytest --cov=app tests/
```

## Test Requirements

Tests require the backend API to be running:

```bash
# Start backend
make up

# In another terminal, run tests
pytest
```

Or run the validation script directly:
```bash
python tests/test_improvements.py
```

## Configuration

Pytest is configured in `pytest.ini` at the project root:
- Test discovery: `tests/test_*.py`
- Verbose output by default
- Short traceback format

Common imports are available in `conftest.py`.
