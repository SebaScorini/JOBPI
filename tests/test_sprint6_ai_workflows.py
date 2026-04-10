from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.db import crud
from app.core.rate_limit import InMemoryRateLimiter
from app.schemas.cv import CvAnalysisResponse


class _StubJobAnalyzer:
    def __call__(self, **_kwargs):
        return SimpleNamespace(
            summary="Concise backend analysis",
            seniority="mid",
            role_type="backend",
            req_skills=["Python", "FastAPI"],
            nice_skills=["Docker"],
            responsibilities=["Build APIs"],
            prep=["Review APIs"],
            learn=["Practice testing"],
            gaps=["Docker"],
            resume=["Highlight APIs"],
            interview=["Explain architecture"],
            projects=["Ship a backend service"],
        )


class _StubCvAnalyzer:
    def analyze(self, *, cv_text: str, language: str = "english", **_kwargs):
        if "strong-profile" in cv_text:
            return CvAnalysisResponse(
                fit_summary="Strong fit for the role.",
                strengths=["Python APIs", "Testing"],
                missing_skills=["Docker"],
                likely_fit_level="strong",
                resume_improvements=["Move API wins higher."],
                interview_focus=["System design"],
                next_steps=["Practice SQL"],
            )

        return CvAnalysisResponse(
            fit_summary="Moderate fit for the role.",
            strengths=["Python basics"],
            missing_skills=["FastAPI", "Testing"],
            likely_fit_level="medium",
            resume_improvements=["Add backend evidence."],
            interview_focus=["Explain projects"],
            next_steps=["Practice API work"],
        )


class _StubCoverLetterGenerator:
    def __init__(self, body: str) -> None:
        self.body = body

    def __call__(self, **_kwargs):
        return SimpleNamespace(cover_letter=self.body)


def _job_rate_limit_settings(limit: int, window_seconds: int = 60) -> SimpleNamespace:
    return SimpleNamespace(
        redis_url=None,
        rate_limit_enabled=True,
        auth_window_seconds=window_seconds,
        auth_register_limit=20,
        auth_login_limit=20,
        job_analyze_limit=limit,
        job_analyze_window_seconds=window_seconds,
        match_cvs_limit=limit,
        match_cvs_window_seconds=window_seconds,
        cover_letter_limit=limit,
        cover_letter_window_seconds=window_seconds,
        should_bypass_user_limits=lambda _email: False,
        is_trusted_user=lambda _email: False,
        max_job_description_chars=500,
        ai_timeout_seconds=10,
    )


def test_job_analysis_success_and_saved_listing(client, auth_headers, monkeypatch):
    import app.services.job_analyzer as job_service_module

    service = job_service_module.get_job_analyzer_service()
    service.analyzer = _StubJobAnalyzer()
    service._cache.clear()

    response = client.post(
        "/jobs/analyze",
        headers=auth_headers(),
        json={
            "title": "Backend Engineer",
            "company": "Acme",
            "description": "Python FastAPI SQL backend testing role with API ownership and collaboration." * 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_result"]["summary"] == "Concise backend analysis"
    assert payload["analysis_result"]["required_skills"] == ["Python", "FastAPI"]


def test_job_analysis_rejects_oversized_description(client, auth_headers, monkeypatch):
    import app.api.routes.jobs as jobs_routes
    import app.core.rate_limit as rate_limit_module

    headers = auth_headers()
    settings = _job_rate_limit_settings(limit=10)
    settings.max_job_description_chars = 120
    monkeypatch.setattr(jobs_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(rate_limit_module, "get_settings", lambda: settings)

    response = client.post(
        "/jobs/analyze",
        headers=headers,
        json={
            "title": "Backend Engineer",
            "company": "Acme",
            "description": "x" * 121,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ERR_VALIDATION"


def test_job_analysis_rate_limit_returns_429(client, auth_headers, monkeypatch):
    import app.api.routes.jobs as jobs_routes
    import app.core.rate_limit as rate_limit_module
    import app.services.job_analyzer as job_service_module

    settings = _job_rate_limit_settings(limit=1)
    monkeypatch.setattr(jobs_routes, "get_settings", lambda: settings)
    monkeypatch.setattr(rate_limit_module, "get_settings", lambda: settings)
    monkeypatch.setattr(rate_limit_module, "_limiter", InMemoryRateLimiter())
    monkeypatch.setattr(rate_limit_module, "_limiter_signature", "test-job-limit")

    service = job_service_module.get_job_analyzer_service()
    service.analyzer = _StubJobAnalyzer()
    service._cache.clear()

    headers = auth_headers()
    payload = {
        "title": "Backend Engineer",
        "company": "Acme",
        "description": "Python FastAPI SQL backend testing role with API ownership and collaboration." * 2,
    }
    first = client.post("/jobs/analyze", headers=headers, json=payload)
    second = client.post("/jobs/analyze", headers=headers, json=payload)

    assert first.status_code == 200
    assert second.status_code == 429


def test_match_and_compare_cvs_are_deterministic(
    client,
    auth_headers,
    test_db,
    seeded_user,
    seeded_job,
    monkeypatch,
):
    import app.services.cv_library_service as cv_library_service_module

    strong_cv = crud.create_cv(
        test_db,
        user_id=seeded_user.id,
        filename="strong.pdf",
        display_name="Strong CV",
        raw_text="strong-profile Python FastAPI testing",
        clean_text="strong-profile Python FastAPI testing",
        summary="Strong summary",
        library_summary="Strong summary",
        tags=[],
    )
    weaker_cv = crud.create_cv(
        test_db,
        user_id=seeded_user.id,
        filename="weaker.pdf",
        display_name="Weaker CV",
        raw_text="generalist profile",
        clean_text="generalist profile",
        summary="Weaker summary",
        library_summary="Weaker summary",
        tags=[],
    )

    service = cv_library_service_module.get_cv_library_service()
    service.cv_analyzer = _StubCvAnalyzer()
    service._analysis_cache.clear()

    headers = auth_headers(email=seeded_user.email)

    match_response = client.post(
        f"/jobs/{seeded_job.id}/match-cvs",
        headers=headers,
        json={"cv_id": strong_cv.id},
    )
    compare_response = client.post(
        f"/jobs/{seeded_job.id}/compare-cvs",
        headers=headers,
        json={"cv_id_a": strong_cv.id, "cv_id_b": weaker_cv.id},
    )

    assert match_response.status_code == 200
    assert match_response.json()["match_level"] == "strong"
    assert compare_response.status_code == 200
    assert compare_response.json()["winner"]["cv_id"] == strong_cv.id


def test_match_job_missing_cv_returns_404(client, auth_headers, seeded_job):
    response = client.post(
        f"/jobs/{seeded_job.id}/match-cvs",
        headers=auth_headers(),
        json={"cv_id": 9999},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ERR_CV_NOT_FOUND"


def test_cover_letter_regenerate_overwrites_cached_value(
    client,
    auth_headers,
    seeded_cv,
    seeded_job,
    monkeypatch,
):
    import app.services.cover_letter_service as cover_letter_service_module

    service = cover_letter_service_module.get_cover_letter_service()
    service.generator = _StubCoverLetterGenerator("First draft for the role.")

    first = client.post(
        f"/jobs/{seeded_job.id}/cover-letter",
        headers=auth_headers(),
        json={"selected_cv_id": seeded_cv.id},
    )

    service.generator = _StubCoverLetterGenerator("Regenerated draft for the role.")
    cached = client.post(
        f"/jobs/{seeded_job.id}/cover-letter",
        headers=auth_headers(),
        json={"selected_cv_id": seeded_cv.id},
    )
    regenerated = client.post(
        f"/jobs/{seeded_job.id}/cover-letter",
        headers=auth_headers(),
        json={"selected_cv_id": seeded_cv.id, "regenerate": True},
    )

    assert first.status_code == 200
    assert cached.status_code == 200
    assert regenerated.status_code == 200
    assert first.json()["generated_cover_letter"] == "First draft for the role."
    assert cached.json()["generated_cover_letter"] == "First draft for the role."
    assert regenerated.json()["generated_cover_letter"] == "Regenerated draft for the role."
