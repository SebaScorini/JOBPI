"""Pytest configuration and fixtures for JOBPI tests."""

import os
import sys
from pathlib import Path

# Add project root to path so imports work correctly
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Keep tests hermetic even when the local .env points at production-style Postgres.
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = f"sqlite:///{(project_root / 'test_jobpi.db').as_posix()}"
