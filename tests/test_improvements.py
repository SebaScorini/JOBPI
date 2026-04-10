"""Regression tests for validation and health improvements."""

import pytest
import requests
from pydantic import ValidationError

from app.schemas.auth import UserRegisterRequest
from app.schemas.cv import PaginationParams


BASE_URL = "http://127.0.0.1:8000"


def test_email_validation():
    """Valid emails are accepted and malformed emails are rejected."""
    req = UserRegisterRequest(email="user@example.com", password="ValidPass123")
    assert req.email == "user@example.com"

    invalid_emails = [
        "notanemail",
        "@example.com",
        "user@",
        "user@.com",
    ]

    for email in invalid_emails:
        with pytest.raises(ValidationError):
            UserRegisterRequest(email=email, password="ValidPass123")


def test_password_validation():
    """Strong passwords pass validation and weak passwords do not."""
    req = UserRegisterRequest(email="user@example.com", password="ValidPass123")
    assert req.password == "ValidPass123"

    invalid_passwords = [
        "pass123",
        "PASS123",
        "PassWord",
        "Pass",
    ]

    for password in invalid_passwords:
        with pytest.raises(ValidationError):
            UserRegisterRequest(email="user@example.com", password=password)


def test_pagination_params():
    """Pagination bounds are enforced and negative offsets clamp safely."""
    params = PaginationParams(limit=20, offset=0)
    assert params.limit == 20
    assert params.offset == 0

    with pytest.raises(ValidationError):
        PaginationParams(limit=0, offset=0)

    with pytest.raises(ValidationError):
        PaginationParams(limit=201, offset=0)

    clamped = PaginationParams(limit=20, offset=-1)
    assert clamped.limit == 20
    assert clamped.offset == 0


def test_api_health():
    """Health endpoint responds when a local API server is available."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
    except requests.RequestException as exc:
        pytest.skip(f"Local API server not running at {BASE_URL}: {exc}")

    assert response.status_code == 200
    assert response.json().get("status") == "ok"
