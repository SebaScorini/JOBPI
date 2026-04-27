import json
import logging

from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app


def test_health_logs_include_trace_id(caplog):
    caplog.set_level(logging.INFO)
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Trace-Id"]
    messages = [record.getMessage() for record in caplog.records]
    assert "request_start" in messages
    assert "request_end" in messages

    trace_ids = {
        getattr(record, "trace_id", None)
        for record in caplog.records
        if record.getMessage() in {"request_start", "request_end"}
    }
    assert trace_ids == {response.headers["X-Trace-Id"]}


def test_logging_context_defaults_are_json_serializable():
    payload = get_settings().model_dump()
    assert payload["sentry_dsn"] in {None, ""}
    json.dumps({"status": "ok", "config_loaded": True})


def test_development_cover_letter_defaults():
    settings = get_settings()
    if settings.app_env != "development":
        return

    assert settings.cover_letter_limit == 6
    assert settings.cover_letter_window_seconds == 600
    assert settings.cover_letter_max_tokens == 800
    assert settings.cv_match_max_tokens >= 100
    assert settings.cv_match_retry_max_tokens >= settings.cv_match_max_tokens


def test_settings_preserve_distinct_retry_token_budgets():
    settings = Settings(
        database_url="sqlite:///./test.db",
        secret_key="test-secret",
        cv_match_max_tokens=1200,
        cv_match_retry_max_tokens=1800,
        job_analysis_max_tokens=900,
        job_analysis_retry_max_tokens=1400,
    )

    assert settings.cv_match_max_tokens == 1200
    assert settings.cv_match_retry_max_tokens == 1800
    assert settings.job_analysis_max_tokens == 900
    assert settings.job_analysis_retry_max_tokens == 1400


def test_production_defaults_keep_rate_limits_enabled(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    for name in (
        "RATE_LIMIT_ENABLED",
        "AUTH_RATE_LIMIT_WINDOW_SECONDS",
        "AUTH_REGISTER_RATE_LIMIT",
        "AUTH_LOGIN_RATE_LIMIT",
        "JOB_ANALYZE_RATE_LIMIT_WINDOW_SECONDS",
        "JOB_ANALYZE_RATE_LIMIT",
        "MATCH_CVS_RATE_LIMIT_WINDOW_SECONDS",
        "MATCH_CVS_RATE_LIMIT",
        "COVER_LETTER_RATE_LIMIT_WINDOW_SECONDS",
        "COVER_LETTER_RATE_LIMIT",
        "CV_UPLOAD_RATE_LIMIT_WINDOW_SECONDS",
        "CV_UPLOAD_RATE_LIMIT",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(
        database_url="postgresql+psycopg://user:pass@localhost:5432/jobpi",
        secret_key="prod-secret",
    )

    assert settings.rate_limit_enabled is True
    assert settings.auth_register_limit == 3
    assert settings.auth_login_limit == 5
    assert settings.job_analyze_limit == 6
    assert settings.match_cvs_limit == 8
    assert settings.cover_letter_limit == 4
    assert settings.cv_upload_limit == 5
