from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.models.ai_schemas import ColdOutreachAIOutput, LinkedInProfileAIOutput


def _fake_structured_ai_call(*, operation: str, **_kwargs):
    if operation == "linkedin_profile_generation":
        return SimpleNamespace(
            payload=LinkedInProfileAIOutput(
                headline="Backend Engineer | Python, FastAPI, SQL",
                about_summary="I build reliable backend APIs and data workflows grounded in Python, FastAPI, and SQL.",
                keywords=["Python", "FastAPI", "SQL"],
                optimization_tips=["Lead with backend impact.", "Mirror target role keywords."],
            )
        )
    if operation == "cold_outreach_generation":
        return SimpleNamespace(
            payload=ColdOutreachAIOutput(
                connection_message="Hi Ana, I saw Acme needs Python/FastAPI depth. My CV maps closely to API and SQL delivery, and I'd value connecting.",
                personalization_notes=["Names the stack.", "Connects CV evidence to the role."],
            )
        )

    raise AssertionError(f"Unexpected AI operation: {operation}")


def _patch_linkedin_ai(monkeypatch):
    import app.services.linkedin_service as linkedin_service_module

    linkedin_service_module._service = None
    service = linkedin_service_module.get_linkedin_service()
    service.profile_generator = lambda **_kwargs: None
    service.outreach_generator = lambda **_kwargs: None

    monkeypatch.setattr(linkedin_service_module, "run_structured_ai_call", _fake_structured_ai_call)
    return service


def test_linkedin_ai_output_normalizers_trim_lists_and_enforce_character_limits():
    profile = LinkedInProfileAIOutput.model_validate(
        {
            "headline": "Backend engineer " * 30,
            "about_summary": "I build APIs.\nI improve SQL systems.",
            "keywords": "Python, FastAPI, SQL, Python",
            "optimization_tips": "Lead with impact.\nUse role keywords.",
        }
    )
    assert len(profile.headline) <= 220
    assert profile.about_summary == "I build APIs. I improve SQL systems."
    assert profile.keywords == ["Python", "FastAPI", "SQL"]
    assert profile.optimization_tips == ["Lead with impact.", "Use role keywords."]

    outreach = ColdOutreachAIOutput.model_validate(
        {
            "connection_message": "A" * 500,
            "personalization_notes": ["Stack match", "Stack match", "Company context", "Role fit"],
        }
    )
    assert len(outreach.connection_message) == 300
    assert outreach.personalization_notes == ["Stack match", "Company context", "Role fit"]




def test_linkedin_profile_optimization_tips_merges_example_continuation_lines():
    profile = LinkedInProfileAIOutput.model_validate(
        {
            "headline": "Backend Engineer",
            "about_summary": "I build APIs.",
            "keywords": ["Python"],
            "optimization_tips": "Quantify achievements where possible\ne.g.\n'improved internal automation by X%' or 'reduced response time by Y%'.",
        }
    )

    assert profile.optimization_tips == [
        "Quantify achievements where possible e.g. 'improved internal automation by X%' or 'reduced response time by Y%'."
    ]


def test_linkedin_request_schema_defaults_and_validation():
    from pydantic import ValidationError

    from app.schemas.linkedin import ColdOutreachRequest, LinkedInProfileRequest

    profile_request = LinkedInProfileRequest.model_validate({"cv_id": 1, "job_ids": None})
    assert profile_request.job_ids == []
    assert profile_request.language == "english"

    outreach_request = ColdOutreachRequest.model_validate(
        {"job_id": 1, "cv_id": 2, "hiring_manager_name": "  Ana   Gomez  "}
    )
    assert outreach_request.hiring_manager_name == "Ana Gomez"

    with pytest.raises(ValidationError):
        LinkedInProfileRequest.model_validate({"cv_id": 1, "job_ids": [1, 2, 3, 4, 5, 6]})



def test_linkedin_service_methods_call_structured_ai(test_db, seeded_user, seeded_cv, seeded_job, monkeypatch):
    service = _patch_linkedin_ai(monkeypatch)

    profile = service.generate_linkedin_profile(
        session=test_db,
        user=seeded_user,
        cv_id=seeded_cv.id,
        job_ids=[seeded_job.id],
        language="english",
    )
    assert profile.headline.startswith("Backend Engineer")
    assert "FastAPI" in profile.keywords

    outreach = service.generate_cold_outreach(
        session=test_db,
        user=seeded_user,
        job_id=seeded_job.id,
        cv_id=seeded_cv.id,
        hiring_manager_name="Ana",
        language="english",
    )
    assert len(outreach.connection_message) <= 300
    assert "Python/FastAPI" in outreach.connection_message




def test_linkedin_service_reuses_cached_profile_without_second_ai_call(
    test_db,
    seeded_user,
    seeded_cv,
    seeded_job,
    monkeypatch,
):
    import app.services.linkedin_service as linkedin_service_module

    calls = {"count": 0}

    def fake_ai_call(*, operation: str, **_kwargs):
        assert operation == "linkedin_profile_generation"
        calls["count"] += 1
        return SimpleNamespace(
            payload=LinkedInProfileAIOutput(
                headline="Cached Backend Engineer",
                about_summary="Cached profile summary.",
                keywords=["Python"],
                optimization_tips=["Keep this cached."],
            )
        )

    linkedin_service_module._service = None
    service = linkedin_service_module.get_linkedin_service()
    service.profile_generator = lambda **_kwargs: None
    monkeypatch.setattr(linkedin_service_module, "run_structured_ai_call", fake_ai_call)

    first = service.generate_linkedin_profile(
        session=test_db,
        user=seeded_user,
        cv_id=seeded_cv.id,
        job_ids=[seeded_job.id],
        language="english",
    )
    second = service.generate_linkedin_profile(
        session=test_db,
        user=seeded_user,
        cv_id=seeded_cv.id,
        job_ids=[seeded_job.id],
        language="english",
    )

    assert first.headline == "Cached Backend Engineer"
    assert second.headline == "Cached Backend Engineer"
    assert calls["count"] == 1


def test_linkedin_service_returns_404_for_missing_cv(test_db, seeded_user, seeded_job, monkeypatch):
    from fastapi import HTTPException

    service = _patch_linkedin_ai(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        service.generate_cold_outreach(
            session=test_db,
            user=seeded_user,
            job_id=seeded_job.id,
            cv_id=99999,
            language="english",
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "CV not found."


def test_linkedin_profile_endpoint_requires_auth(client, seeded_cv, seeded_job):
    response = client.post(
        "/linkedin/profile",
        json={"cv_id": seeded_cv.id, "job_ids": [seeded_job.id], "language": "english"},
    )
    assert response.status_code in (401, 403)


def test_linkedin_profile_endpoint_success(client, auth_headers, seeded_cv, seeded_job, monkeypatch):
    _patch_linkedin_ai(monkeypatch)
    headers = auth_headers()

    response = client.post(
        "/linkedin/profile",
        headers=headers,
        json={"cv_id": seeded_cv.id, "job_ids": [seeded_job.id], "language": "english"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["headline"] == "Backend Engineer | Python, FastAPI, SQL"
    assert payload["keywords"] == ["Python", "FastAPI", "SQL"]


def test_linkedin_profile_cached_endpoint_returns_saved_result(client, auth_headers, seeded_cv, seeded_job, monkeypatch):
    _patch_linkedin_ai(monkeypatch)
    headers = auth_headers()

    generated = client.post(
        "/linkedin/profile",
        headers=headers,
        json={"cv_id": seeded_cv.id, "job_ids": [seeded_job.id], "language": "english"},
    )
    assert generated.status_code == 200, generated.text

    cached = client.get(
        f"/linkedin/profile?cv_id={seeded_cv.id}&job_ids={seeded_job.id}&language=english",
        headers=headers,
    )

    assert cached.status_code == 200, cached.text
    assert cached.json()["headline"] == "Backend Engineer | Python, FastAPI, SQL"


def test_linkedin_outreach_endpoint_success_and_character_limit(client, auth_headers, seeded_cv, seeded_job, monkeypatch):
    _patch_linkedin_ai(monkeypatch)
    headers = auth_headers()

    response = client.post(
        "/linkedin/outreach",
        headers=headers,
        json={
            "job_id": seeded_job.id,
            "cv_id": seeded_cv.id,
            "hiring_manager_name": "Ana",
            "language": "english",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload["connection_message"]) <= 300
    assert payload["personalization_notes"]



def test_linkedin_endpoint_uses_job_analyze_rate_policy(
    client,
    auth_headers,
    seeded_cv,
    seeded_job,
    monkeypatch,
):
    import app.api.routes.linkedin as linkedin_routes

    _patch_linkedin_ai(monkeypatch)
    captured = {}

    def fake_enforce_rate_limit(*, request, policy, user=None, email=None):
        captured["policy_name"] = policy.name
        captured["limit"] = policy.limit
        captured["window_seconds"] = policy.window_seconds

    monkeypatch.setattr(linkedin_routes, "enforce_rate_limit", fake_enforce_rate_limit)
    headers = auth_headers()

    response = client.post(
        "/linkedin/profile",
        headers=headers,
        json={"cv_id": seeded_cv.id, "job_ids": [seeded_job.id], "language": "english"},
    )

    assert response.status_code == 200, response.text
    assert captured["policy_name"] == "job_analyze"
    assert captured["limit"] > 0
    assert captured["window_seconds"] >= 60


def test_linkedin_endpoint_returns_404_for_missing_job(client, auth_headers, seeded_cv, monkeypatch):
    _patch_linkedin_ai(monkeypatch)
    headers = auth_headers()

    response = client.post(
        "/linkedin/outreach",
        headers=headers,
        json={"job_id": 99999, "cv_id": seeded_cv.id, "language": "english"},
    )

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "ERR_JOB_NOT_FOUND"
