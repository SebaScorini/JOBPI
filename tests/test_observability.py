import json
import logging

from fastapi.testclient import TestClient

from app.core.config import get_settings
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
    assert settings.cover_letter_max_tokens == 640
    assert settings.cv_match_max_tokens == 900
    assert settings.cv_match_retry_max_tokens >= settings.cv_match_max_tokens
