from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.core.security import create_access_token
from app.core.rate_limit import InMemoryRateLimiter


def _rate_limit_settings(limit: int, window_seconds: int = 60) -> SimpleNamespace:
    return SimpleNamespace(
        redis_url=None,
        rate_limit_enabled=True,
        auth_window_seconds=window_seconds,
        auth_register_limit=limit,
        auth_login_limit=limit,
        cv_upload_limit=limit,
        cv_upload_window_seconds=window_seconds,
        is_trusted_user=lambda _email: False,
        should_bypass_user_limits=lambda _email: False,
        max_pdf_size_bytes=1024 * 1024,
        max_pdf_size_mb=1,
    )


def test_register_login_and_duplicate_email_flow(client):
    register_response = client.post(
        "/auth/register",
        json={"email": "sprint6@example.com", "password": "ValidPass123"},
    )
    assert register_response.status_code == 201
    assert register_response.json()["email"] == "sprint6@example.com"

    duplicate_response = client.post(
        "/auth/register",
        json={"email": "sprint6@example.com", "password": "ValidPass123"},
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error"]["code"] == "ERR_CONFLICT"

    login_response = client.post(
        "/auth/login",
        data={"username": "sprint6@example.com", "password": "ValidPass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["token_type"] == "bearer"
    assert login_response.json()["access_token"]


def test_login_rejects_incorrect_password(client):
    client.post("/auth/register", json={"email": "login-test@example.com", "password": "ValidPass123"})

    response = client.post(
        "/auth/login",
        data={"username": "login-test@example.com", "password": "WrongPass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ERR_UNAUTHORIZED"


def test_expired_token_returns_401(client, create_user):
    user = create_user(email="expired@example.com")
    expired_token = create_access_token(str(user.id), expires_delta=timedelta(minutes=-5))

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ERR_UNAUTHORIZED"


def test_login_rate_limit_returns_429(client, create_user, monkeypatch):
    import app.api.routes.auth as auth_routes
    import app.core.rate_limit as rate_limit_module

    create_user(email="limited@example.com")
    settings = _rate_limit_settings(limit=1)

    monkeypatch.setattr(auth_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(rate_limit_module, "get_settings", lambda: settings)
    monkeypatch.setattr(rate_limit_module, "_limiter", InMemoryRateLimiter())
    monkeypatch.setattr(rate_limit_module, "_limiter_signature", "test-limit")

    first = client.post(
        "/auth/login",
        data={"username": "limited@example.com", "password": "WrongPass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    second = client.post(
        "/auth/login",
        data={"username": "limited@example.com", "password": "WrongPass123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert first.status_code == 401
    assert second.status_code == 429
    assert second.headers["Retry-After"]


def test_upload_valid_pdf_returns_cv(client, auth_headers, monkeypatch):
    import app.services.cv_library_service as cv_service_module

    monkeypatch.setattr(cv_service_module, "extract_raw_pdf_text", lambda _file_bytes: "Python FastAPI SQL")
    monkeypatch.setattr(cv_service_module, "preprocess_cv_text", lambda raw_text, max_chars=None: raw_text[:max_chars])

    response = client.post(
        "/cvs/upload",
        headers=auth_headers(),
        files={"file": ("resume.pdf", b"%PDF-1.4 fake", "application/pdf")},
        data={"display_name": "Primary Resume"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["display_name"] == "Primary Resume"
    assert payload["summary"]
    assert payload["library_summary"]


def test_upload_rejects_non_pdf_file(client, auth_headers):
    response = client.post(
        "/cvs/upload",
        headers=auth_headers(),
        files={"file": ("notes.txt", b"plain text", "text/plain")},
        data={"display_name": "Wrong File"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ERR_VALIDATION"


def test_upload_rejects_oversized_pdf(client, auth_headers, monkeypatch):
    import app.api.routes.cvs as cvs_routes
    import app.core.rate_limit as rate_limit_module

    headers = auth_headers()
    settings = SimpleNamespace(
        redis_url=None,
        rate_limit_enabled=False,
        cv_upload_limit=20,
        cv_upload_window_seconds=60,
        max_pdf_size_bytes=8,
        max_pdf_size_mb=1,
        should_bypass_user_limits=lambda _email: False,
        is_trusted_user=lambda _email: False,
    )
    monkeypatch.setattr(cvs_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(rate_limit_module, "get_settings", lambda: settings)

    response = client.post(
        "/cvs/upload",
        headers=headers,
        files={"file": ("resume.pdf", b"123456789", "application/pdf")},
        data={"display_name": "Too Large"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "ERR_PAYLOAD_TOO_LARGE"


def test_batch_upload_allows_partial_success(client, auth_headers, monkeypatch):
    import app.services.cv_library_service as cv_service_module

    monkeypatch.setattr(cv_service_module, "extract_raw_pdf_text", lambda _file_bytes: "Python FastAPI SQL")
    monkeypatch.setattr(cv_service_module, "preprocess_cv_text", lambda raw_text, max_chars=None: raw_text[:max_chars])

    response = client.post(
        "/cvs/batch-upload",
        headers=auth_headers(),
        files=[
            ("files", ("good.pdf", b"%PDF-1.4 ok", "application/pdf")),
            ("files", ("bad.txt", b"text", "text/plain")),
        ],
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["summary"] == {"succeeded": 1, "failed": 1}
    assert payload["results"][0]["success"] is True
    assert payload["results"][1]["success"] is False


def test_batch_upload_keeps_each_cv_summary_isolated(client, auth_headers, monkeypatch):
    import app.services.cv_library_summary_service as cv_summary_module

    raw_text_by_bytes = {
        b"%PDF-1.4 backend": "Python FastAPI engineer\nBuilt backend services",
        b"%PDF-1.4 frontend": "React TypeScript engineer\nBuilt frontend interfaces",
    }

    monkeypatch.setattr(
        "app.services.cv_library_service.extract_raw_pdf_text",
        lambda file_bytes: raw_text_by_bytes[file_bytes],
    )
    monkeypatch.setattr(
        "app.services.cv_library_service.preprocess_cv_text",
        lambda raw_text, max_chars=None: raw_text[:max_chars],
    )

    class _LeakySummaryModule:
        def __init__(self) -> None:
            self._first_result = None

        def __call__(self, *, cv: str, max_tokens: int | None = None):
            if self._first_result is None:
                headline = cv.splitlines()[0].strip()
                self._first_result = SimpleNamespace(summary=f"{headline} summary")
            return self._first_result

    def _call_summary_generator(**kwargs):
        return kwargs["callable_"](cv=kwargs["cv"], max_tokens=kwargs["max_tokens"])

    with (
        patch.object(cv_summary_module, "configure_dspy", return_value=None),
        patch.object(cv_summary_module, "CvLibrarySummaryModule", _LeakySummaryModule),
        patch.object(cv_summary_module, "run_ai_call_with_timeout", side_effect=_call_summary_generator),
    ):
        response = client.post(
            "/cvs/batch-upload",
            headers=auth_headers(),
            files=[
                ("files", ("backend.pdf", b"%PDF-1.4 backend", "application/pdf")),
                ("files", ("frontend.pdf", b"%PDF-1.4 frontend", "application/pdf")),
            ],
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["summary"] == {"succeeded": 2, "failed": 0}
    assert payload["results"][0]["cv"]["library_summary"] != payload["results"][1]["cv"]["library_summary"]
    assert "Python" in payload["results"][0]["cv"]["library_summary"]
    assert "React" in payload["results"][1]["cv"]["library_summary"]
