"""Pytest configuration and fixtures for JOBPI tests."""

import sys
from pathlib import Path

# Add project root to path so imports work correctly
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
