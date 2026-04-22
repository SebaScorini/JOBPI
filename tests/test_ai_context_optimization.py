import logging
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import dspy
from fastapi import HTTPException
import pytest

import app.core.ai as ai_module
import app.services.cover_letter_service as cover_letter_module
from app.core.ai import run_ai_call_with_circuit_breaker, validate_ai_output
from app.core.circuit_breaker import AICircuitBreaker, CircuitBreakerConfig
from app.models.ai_schemas import AIOutputValidationFailure, CvAnalysisAIOutput, CvLibrarySummaryAIOutput, JobAnalysisAIOutput
from app.schemas.job import JobAnalysisRequest
from app.services.cover_letter_service import CoverLetterService
from app.services.cv_analyzer import CvAnalyzerService
from app.services.job_analyzer import JobAnalyzerService
from app.services.job_preprocessing import build_cv_excerpt, build_job_excerpt, clean_description


def test_clean_description_keeps_high_signal_sections_and_drops_fluff():
    description = """
    ABOUT THE ROLE:
    Build backend APIs for a product analytics platform.
    REQUIREMENTS:
    Python and FastAPI experience with SQL and PostgreSQL.
    RESPONSIBILITIES:
    Build APIs and lead backend delivery.
    RESPONSIBILITIES:
    Build APIs and lead backend delivery.
    BENEFITS:
    Medical, dental, and wellness perks.
    Equal opportunity employer statement for all qualified applicants.
    """

    cleaned = clean_description(description)

    assert "Python and FastAPI" in cleaned
    assert "Build APIs and lead backend delivery" in cleaned
    assert "BENEFITS" not in cleaned
    assert "Equal opportunity" not in cleaned
    assert cleaned.count("Build APIs and lead backend delivery") == 1


def test_context_builders_are_deterministic_and_preserve_role_evidence():
    job_text = """
    ABOUT THE ROLE:
    Build backend APIs for an internal platform.
    REQUIREMENTS:
    Python, FastAPI, SQL, PostgreSQL, and Docker.
    RESPONSIBILITIES:
    Own API delivery, improve latency, and collaborate with product.
    BENEFITS:
    Remote stipend and wellness allowance.
    """
    cv_text = """
    SUMMARY
    Product-minded backend engineer.
    EXPERIENCE
    Built FastAPI services and PostgreSQL workflows that reduced latency by 35%.
    Led API integrations for internal analytics tools.
    PROJECTS
    Shipped a Dockerized backend service for job application automation.
    HOBBIES
    Chess club captain and community volunteering.
    """

    job_excerpt = build_job_excerpt(job_text, max_chars=190)
    cv_excerpt = build_cv_excerpt(
        cv_text,
        summary="Backend engineer with Python and FastAPI delivery.",
        library_summary="Backend engineer with Python and FastAPI delivery.",
        job_description=job_excerpt,
        max_chars=240,
    )

    assert job_excerpt == build_job_excerpt(job_text, max_chars=190)
    assert cv_excerpt == build_cv_excerpt(
        cv_text,
        summary="Backend engineer with Python and FastAPI delivery.",
        library_summary="Backend engineer with Python and FastAPI delivery.",
        job_description=job_excerpt,
        max_chars=240,
    )
    assert "Python" in job_excerpt
    assert "Benefits" not in job_excerpt
    assert "## Job Description" in job_excerpt
    assert "Backend engineer with Python and FastAPI delivery." in cv_excerpt
    assert "Built FastAPI services" in cv_excerpt
    assert "Chess club" not in cv_excerpt
    assert "## CV Summary" in cv_excerpt
    assert "## CV Content" in cv_excerpt


def test_job_analysis_retry_uses_retry_budget_and_full_context(monkeypatch):
    monkeypatch.setattr(
        ai_module,
        "_ai_circuit_breaker",
        AICircuitBreaker(
            config=CircuitBreakerConfig(max_retries=1, initial_backoff_ms=0, max_backoff_ms=0),
            sleep_func=lambda _seconds: None,
        ),
    )

    calls: list[dict[str, object]] = []

    class FlakyAnalyzer:
        def __call__(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise HTTPException(status_code=503, detail="temporary failure")
            return SimpleNamespace(
                summary="Strong backend role fit.",
                seniority="mid",
                role_type="backend",
                req_skills=["Python", "FastAPI"],
                nice_skills=["Docker"],
                responsibilities=["Build APIs"],
                prep=["Review APIs"],
                learn=["Practice testing"],
                gaps=["Docker"],
                resume=["Highlight API impact"],
                interview=["Discuss system design"],
                projects=["Ship a backend service"],
            )

    service = JobAnalyzerService()
    service.analyzer = FlakyAnalyzer()
    service.max_tokens = 900
    service.retry_max_tokens = 420
    service.retry_description_chars = 900

    description = "REQUIREMENTS:\n" + "\n".join(
        f"Requirement {index}: Python FastAPI SQL backend API ownership, observability, testing, and Docker delivery."
        for index in range(18)
    )

    try:
        result = service.analyze(
            JobAnalysisRequest(
                title="Backend Engineer",
                company="Acme",
                description=description,
            )
        )
    finally:
        service._executor.shutdown(wait=False, cancel_futures=True)

    assert len(calls) == 2
    assert calls[0]["max_tokens"] == 900
    assert calls[1]["max_tokens"] == 420
    assert str(calls[1]["description"]) == str(calls[0]["description"])
    assert "Requirement 17" in str(calls[0]["description"])
    assert result.analysis_result.summary == "Strong backend role fit."


def test_ai_observability_logs_retry_usage_and_latency(caplog, monkeypatch):
    monkeypatch.setattr(
        ai_module,
        "_ai_circuit_breaker",
        AICircuitBreaker(
            config=CircuitBreakerConfig(max_retries=1, initial_backoff_ms=0, max_backoff_ms=0),
            sleep_func=lambda _seconds: None,
        ),
    )

    caplog.set_level(logging.INFO)
    logger = logging.getLogger("tests.ai_context_optimization")
    state = {"calls": 0}

    def flaky_call(**kwargs):
        state["calls"] += 1
        if state["calls"] == 1:
            raise HTTPException(status_code=503, detail="retry")
        return {"usage": {"prompt_tokens": 123, "completion_tokens": 45, "total_tokens": 168}}

    executor = ThreadPoolExecutor(max_workers=1)
    try:
        result = run_ai_call_with_circuit_breaker(
            executor=executor,
            timeout_seconds=5,
            operation="test_ai_call",
            logger=logger,
            callable_=flaky_call,
            lm_max_tokens=500,
            retry_lm_max_tokens=280,
            attempt_kwargs_builder=lambda attempt: {
                "prompt": "Python FastAPI SQL backend role " * (8 if attempt == 0 else 4),
                "max_tokens": 500 if attempt == 0 else 280,
            },
        )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    messages = [record.getMessage() for record in caplog.records]

    assert result["usage"]["total_tokens"] == 168
    assert any("ai_call_start operation=test_ai_call" in message for message in messages)
    assert any("ai_retry operation=test_ai_call retry=1" in message for message in messages)
    assert any("reason=http_503" in message for message in messages)
    assert any("ai_call_complete operation=test_ai_call" in message for message in messages)
    assert any("provider_total_tokens=168" in message for message in messages)


def test_job_analysis_switches_to_provider_fallback_model_on_provider_unavailable(monkeypatch):
    monkeypatch.setattr(
        ai_module,
        "_ai_circuit_breaker",
        AICircuitBreaker(
            config=CircuitBreakerConfig(max_retries=1, initial_backoff_ms=0, max_backoff_ms=0),
            sleep_func=lambda _seconds: None,
        ),
    )

    calls: list[dict[str, object]] = []

    class ProviderFlakyAnalyzer:
        def __call__(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise RuntimeError("OpenrouterException: service unavailable")
            return SimpleNamespace(
                summary="Strong backend role fit.",
                seniority="mid",
                role_type="backend",
                req_skills=["Python", "FastAPI"],
                nice_skills=["Docker"],
                responsibilities=["Build APIs"],
                prep=["Review APIs"],
                learn=["Practice testing"],
                gaps=["Docker"],
                resume=["Highlight API impact"],
                interview=["Discuss system design"],
                projects=["Ship a backend service"],
            )

    service = JobAnalyzerService()
    service.analyzer = ProviderFlakyAnalyzer()

    try:
        result = service.analyze(
            JobAnalysisRequest(
                title="Backend Engineer",
                company="Acme",
                description="Python FastAPI SQL backend role with API ownership and testing responsibilities." * 3,
            )
        )
    finally:
        service._executor.shutdown(wait=False, cancel_futures=True)

    assert len(calls) == 2
    assert calls[0]["model"] == ai_module.get_settings().dspy_model
    assert calls[1]["model"] == ai_module.get_settings().dspy_provider_fallback_model
    assert result.analysis_result.summary == "Strong backend role fit."


def test_job_analysis_auth_failure_returns_explicit_error_without_traceback(caplog):
    class AuthFailureAnalyzer:
        def __call__(self, **kwargs):
            raise RuntimeError(
                'litellm.AuthenticationError: AuthenticationError: OpenrouterException - {"error":{"message":"User not found.","code":401}}'
            )

    service = JobAnalyzerService()
    service.analyzer = AuthFailureAnalyzer()

    caplog.set_level(logging.WARNING)
    try:
        try:
            service.analyze(
                JobAnalysisRequest(
                    title="Backend Engineer",
                    company="Acme",
                    description="Python FastAPI SQL backend role with API ownership and testing responsibilities." * 3,
                )
            )
        except HTTPException as exc:
            error = exc
        else:
            raise AssertionError("Expected analyze() to raise HTTPException")
    finally:
        service._executor.shutdown(wait=False, cancel_futures=True)

    messages = [record.getMessage() for record in caplog.records]

    assert error.status_code == 503
    assert error.detail == "AI analysis is not configured."
    assert any("ai_call_failed operation=job_analysis reason=auth" in message for message in messages)
    assert not any(record.exc_info for record in caplog.records if "reason=auth" in record.getMessage())


def test_job_analysis_refreshes_persisted_fallback_result_without_cache_reuse(test_db, seeded_user):
    from app.db import crud

    stored = crud.create_job_analysis(
        test_db,
        user_id=seeded_user.id,
        title="Backend Engineer",
        company="Acme",
        description="Python FastAPI SQL backend testing role." * 3,
        clean_description="Python FastAPI SQL backend testing role." * 3,
        analysis_result={
            "summary": "Fallback summary.",
            "seniority": "unknown",
            "role_type": "generalist",
            "required_skills": ["Communication"],
            "nice_to_have_skills": [],
            "responsibilities": ["Cross-functional delivery"],
            "how_to_prepare": ["Prepare 2-3 stories showing direct ownership of similar business-critical work."],
            "learning_path": [],
            "missing_skills": [],
            "resume_tips": ["Move your strongest evidence into the summary and most recent experience section."],
            "interview_tips": ["Expect detailed questions on core technical skills and how you applied them in production."],
            "portfolio_project_ideas": ["Build an internal operations dashboard that pulls from APIs and SQL sources, with role-based access and audit-friendly workflows."],
            "_language": "english",
            "_fallback": True,
        },
    )

    class FreshAnalyzer:
        def __call__(self, **_kwargs):
            return SimpleNamespace(
                summary="Strong backend role fit.",
                seniority="mid",
                role_type="backend",
                req_skills=["Python", "FastAPI"],
                nice_skills=["Docker"],
                responsibilities=["Build APIs"],
                prep=["Review APIs"],
                learn=["Practice testing"],
                gaps=["Docker"],
                resume=["Highlight API impact"],
                interview=["Discuss system design"],
                projects=["Ship a backend service"],
            )

    service = JobAnalyzerService()
    service.analyzer = FreshAnalyzer()

    try:
        result = service.analyze(
            JobAnalysisRequest(
                title="Backend Engineer",
                company="Acme",
                description="Python FastAPI SQL backend testing role." * 3,
            ),
            session=test_db,
            user=seeded_user,
        )
    finally:
        service._executor.shutdown(wait=False, cancel_futures=True)

    assert result.id == stored.id
    assert result.analysis_result.summary == "Strong backend role fit."
    refreshed = crud.get_job_for_user(test_db, seeded_user.id, stored.id)
    assert refreshed is not None
    assert refreshed.analysis_result["summary"] == "Strong backend role fit."
    assert refreshed.analysis_result.get("_fallback") is not True


def test_job_analysis_fallback_keeps_full_stack_description_readable():
    description = """As a Full Stack Developer, you will be responsible for designing, developing, and maintaining both the front-end and back-end components of our applications. You will work closely with cross-functional teams to deliver high-quality software solutions.

Develop and maintain web applications
Collaborate with UX/UI designers to implement user-friendly interfaces
Integrate APIs and third-party services
Optimize applications for maximum speed and scalability
Participate in code reviews and contribute to team knowledge sharing

Team Structure: You will be part of a dynamic team of developers, designers, and product managers.

Ideal Profile

The ideal candidate will have a strong technical background and a passion for problem-solving.

Experience with JavaScript frameworks (e.g., React, Angular)
Proficiency in server-side languages (e.g., Node.js, Python)
Familiarity with database management (e.g., SQL, NoSQL)
Understanding of RESTful APIs
Version control systems (e.g., Git)

Soft Skills

Communication
Problem Solving

Education: Bachelor’s degree in Computer Science or related field preferred."""

    service = JobAnalyzerService()
    try:
        payload = service._build_fallback_analysis_payload(
            title="Full Stack Developer",
            company="Hey Support",
            cleaned_description=description,
            language="english",
        )
    finally:
        service._executor.shutdown(wait=False, cancel_futures=True)

    joined_skills = " ".join(payload.required_skills).lower()

    assert "python" in joined_skills
    assert "react" in joined_skills or "api" in joined_skills
    assert not any(item.strip().endswith(",") for item in payload.responsibilities)
    assert not any(len(item.strip()) < 12 for item in payload.responsibilities)
    assert any("web applications" in item.lower() for item in payload.responsibilities)
    assert any("integrate apis" in item.lower() for item in payload.responsibilities)
    assert not any(item.lower().startswith("team structure") for item in payload.responsibilities)


def test_job_analysis_fallback_extracts_retool_data_and_governance_signals():
    description = """
    RESPONSIBILITIES
    Partner closely with Product and Engineering to design, build, and deploy Retool applications that automate operational workflows and support key business functions.
    Translate business requirements into scalable internal tools that improve efficiency, reduce manual processes, and enhance data visibility across teams.
    Build and maintain integrations between Retool and internal systems (APIs, databases, and third-party platforms).
    Collaborate with stakeholders across operations, compliance, and technology to identify high-impact automation opportunities and deliver solutions quickly.
    Ensure applications follow established SDLC, security, and governance standards, particularly in a regulated banking environment.

    QUALIFICATIONS
    4+ years of experience as a software engineer or similar experience building software projects.
    Proven experience managing data migration or data modernization projects.
    Must have strong SQL skills.
    Must have JavaScript skills.
    Understanding of data modeling concepts, batch and streaming transformation processes, data governance frameworks (Apache Ranger, Immuta, Unity Catalog),
    data quality frameworks (great expectations), monitoring and observability platforms (datadog), cloud providers (AWS, GCP), data platforms and frameworks
    (Apache Spark, Databricks, Presto, EMR).
    Databricks certification.
    Experience with tools like Jira, Confluence, Notion.
    Experience working in regulated or enterprise environments with strict data governance.
    """

    service = JobAnalyzerService()
    try:
        payload = service._build_fallback_analysis_payload(
            title="Full Stack Engineer",
            company="Parser",
            cleaned_description=description,
            language="english",
        )
    finally:
        service._executor.shutdown(wait=False, cancel_futures=True)

    required_skills = " ".join(payload.required_skills)
    all_text = " ".join(
        [
            payload.summary,
            *payload.required_skills,
            *payload.nice_to_have_skills,
            *payload.how_to_prepare,
            *payload.learning_path,
            *payload.missing_skills,
            *payload.resume_tips,
            *payload.interview_tips,
            *payload.portfolio_project_ideas,
        ]
    ).lower()

    assert payload.seniority == "mid"
    assert payload.role_type in {"data", "operations", "generalist"}
    assert "Retool" in required_skills
    assert "SQL" in required_skills
    assert "JavaScript" in required_skills
    assert "databricks" in all_text
    assert "governance" in all_text or "regulated" in all_text
    assert any("operational workflows" in item.lower() for item in payload.responsibilities)
    assert len(payload.resume_tips) >= 3
    assert len(payload.interview_tips) >= 3


def test_cv_analyzer_uses_cleaned_job_and_cv_context():
    captured: dict[str, object] = {}

    class CaptureAnalyzer:
        def __call__(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                fit_summary="Strong fit for the role.",
                strengths=["Python APIs", "Testing"],
                missing_skills=["Docker"],
                likely_fit_level="Strong",
                resume_improvements=["Move API wins higher."],
                interview_focus=["System design"],
                next_steps=["Practice SQL"],
            )

    service = CvAnalyzerService()
    service.analyzer = CaptureAnalyzer()
    service.max_tokens = 720
    job_description = """
    ABOUT THE ROLE:
    Build backend APIs for a hiring workflow platform.
    REQUIREMENTS:
    Python, FastAPI, SQL, PostgreSQL, and observability.
    RESPONSIBILITIES:
    Improve API latency and partner with product.
    BENEFITS:
    Wellness allowance and team retreats.
    """
    cv_text = """
    SUMMARY
    Backend engineer focused on Python services.
    EXPERIENCE
    Built FastAPI APIs that improved response time by 35%.
    Led PostgreSQL and SQL migrations for production systems.
    PROJECTS
    Shipped a Dockerized application workflow assistant.
    HOBBIES
    Chess club captain and marathon training.
    """

    try:
        response = service.analyze(
            job_title="Backend Engineer",
            job_description=job_description,
            cv_text=cv_text,
        )
    finally:
        service._executor.shutdown(wait=False, cancel_futures=True)

    assert response.fit_summary == "Strong fit for the role."
    assert "Python" in str(captured["job_description"])
    assert "Benefits" not in str(captured["job_description"])
    assert "Chess club" not in str(captured["cv_text"])
    assert "Shipped a Dockerized application workflow assistant." in str(captured["cv_text"])


def test_cv_analysis_retry_uses_retry_budget_and_full_context(monkeypatch):
    monkeypatch.setattr(
        ai_module,
        "_ai_circuit_breaker",
        AICircuitBreaker(
            config=CircuitBreakerConfig(max_retries=1, initial_backoff_ms=0, max_backoff_ms=0),
            sleep_func=lambda _seconds: None,
        ),
    )

    calls: list[dict[str, object]] = []

    class FlakyCvAnalyzer:
        def __call__(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise HTTPException(status_code=503, detail="temporary failure")
            return SimpleNamespace(
                fit_summary="Strong fit for the role.",
                strengths=["Python APIs", "Testing"],
                missing_skills=["Docker"],
                likely_fit_level="Strong",
                resume_improvements=["Move API wins higher."],
                interview_focus=["System design"],
                next_steps=["Practice SQL"],
            )

    service = CvAnalyzerService()
    service.analyzer = FlakyCvAnalyzer()
    service.max_tokens = 720
    service.retry_max_tokens = 960

    job_description = "REQUIREMENTS:\n" + "\n".join(
        f"Requirement {index}: Python FastAPI SQL PostgreSQL backend APIs, testing, observability, and collaboration."
        for index in range(18)
    )
    cv_text = "EXPERIENCE\n" + "\n".join(
        f"Project {index}: Built Python FastAPI APIs, improved latency by 20%, and owned SQL delivery for production systems."
        for index in range(18)
    )

    try:
        result = service.analyze(
            job_title="Backend Engineer",
            job_description=job_description,
            cv_text=cv_text,
        )
    finally:
        service._executor.shutdown(wait=False, cancel_futures=True)

    assert len(calls) == 2
    assert calls[0]["max_tokens"] == 720
    assert calls[1]["max_tokens"] == 960
    assert str(calls[1]["job_description"]) == str(calls[0]["job_description"])
    assert str(calls[1]["cv_text"]) == str(calls[0]["cv_text"])
    assert "Requirement 17" in str(calls[0]["job_description"])
    assert "Project 17" in str(calls[0]["cv_text"])
    assert result.fit_summary == "Strong fit for the role."


def test_cover_letter_generation_uses_full_context_and_cached_summary(monkeypatch):
    captured: dict[str, object] = {}

    class CaptureGenerator:
        def __call__(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                cover_letter=(
                    "Dear Acme team,\n\n"
                    "I am excited to apply for the Backend Engineer role.\n\n"
                    "Thank you for your time and consideration."
                )
            )

    service = CoverLetterService()
    service.generator = CaptureGenerator()
    service.max_tokens = 480

    job = SimpleNamespace(
        id=1,
        title="Backend Engineer",
        company="Acme",
        clean_description="""
        ABOUT THE ROLE:
        Build backend APIs for an internal platform.
        REQUIREMENTS:
        Python, FastAPI, SQL, PostgreSQL, and Docker.
        RESPONSIBILITIES:
        Improve API reliability and delivery speed.
        BENEFITS:
        Wellness allowance and home office stipend.
        """,
    )
    cv = SimpleNamespace(
        id=7,
        summary="Short backend summary.",
        library_summary="Backend engineer with Python and FastAPI delivery.",
        clean_text="""
        SUMMARY
        Backend engineer focused on Python systems.
        EXPERIENCE
        Built FastAPI services and PostgreSQL tooling that improved throughput by 35%.
        PROJECTS
        Shipped a Dockerized workflow assistant for job applications.
        HOBBIES
        Chess club captain.
        """,
    )

    monkeypatch.setattr(cover_letter_module.crud, "get_job_for_user", lambda session, user_id, job_id: job)
    monkeypatch.setattr(cover_letter_module.crud, "get_cv_for_user", lambda session, user_id, cv_id: cv)
    monkeypatch.setattr(cover_letter_module.crud, "get_cached_cover_letter", lambda **kwargs: None)
    monkeypatch.setattr(cover_letter_module.crud, "update_job_cover_letter", lambda **kwargs: None)

    try:
        output = service.generate_cover_letter(
            session=object(),
            user=SimpleNamespace(id=123),
            job_id=job.id,
            selected_cv_id=cv.id,
        )
    finally:
        service._executor.shutdown(wait=False, cancel_futures=True)

    assert output.startswith("Dear Acme team")
    assert captured["cv_summary"] == "Backend engineer with Python and FastAPI delivery."
    assert "## Job Description" in str(captured["job_description"])
    assert "## CV Content" in str(captured["cv_text"])
    assert "Benefits" not in str(captured["job_description"])
    assert "Chess club" not in str(captured["cv_text"])


def test_validate_ai_output_preserves_raw_payload_on_schema_failure(caplog):
    caplog.set_level(logging.WARNING)
    logger = logging.getLogger("tests.ai_schema_validation")

    with pytest.raises(AIOutputValidationFailure) as exc_info:
        validate_ai_output(
            result={"summary": 123, "extra": "field"},
            schema=CvLibrarySummaryAIOutput,
            operation="cv_library_summary",
            logger=logger,
        )

    failure = exc_info.value
    assert failure.failure_category == "schema_validation_failed"
    assert failure.schema_name == "CvLibrarySummaryAIOutput"
    assert failure.raw_output == {"summary": 123, "extra": "field"}
    assert any(issue.field_path in {"summary", "extra"} for issue in failure.issues)
    assert any("schema_validation_success=false" in record.getMessage() for record in caplog.records)


def test_validate_ai_output_handles_dspy_prediction_store(caplog):
    caplog.set_level(logging.INFO)
    logger = logging.getLogger("tests.ai_prediction_validation")
    prediction = dspy.Prediction(
        summary="Strong backend role fit.",
        seniority="mid",
        role_type="backend",
        req_skills=["Python", "FastAPI"],
        nice_skills=["Docker"],
        responsibilities=["Build APIs"],
        prep=["Review APIs"],
        learn=["Practice testing"],
        gaps=["Docker"],
        resume=["Highlight API impact"],
        interview=["Discuss system design"],
        projects=["Ship a backend service"],
    )

    parsed = validate_ai_output(
        result=prediction,
        schema=JobAnalysisAIOutput,
        operation="job_analysis",
        logger=logger,
    )

    assert parsed.payload.summary == "Strong backend role fit."
    assert parsed.raw_output["role_type"] == "backend"


def test_validate_ai_output_parses_fenced_json_and_normalizes_cv_labels(caplog):
    caplog.set_level(logging.INFO)
    logger = logging.getLogger("tests.ai_fenced_json_validation")

    raw_output = """
```json
{
  "fit_summary": "Strong fit for this backend role.",
        "strengths": "Python\\nFastAPI",
  "missing_skills": ["Docker"],
  "fit_level": "very strong",
  "resume_improvements": "Add Docker evidence, strengthen deployment stories",
  "ats_improvements": null,
  "recruiter_improvements": ["Quantify backend impact"],
  "rewritten_bullets": ["Built FastAPI services"],
  "interview_focus": "Explain scaling tradeoffs",
  "next_steps": "Apply with the backend version of the CV"
}
```
"""

    parsed = validate_ai_output(
        result=raw_output,
        schema=CvAnalysisAIOutput,
        operation="cv_match_analysis",
        logger=logger,
    )

    assert parsed.payload.fit_summary == "Strong fit for this backend role."
    assert parsed.payload.strengths == ["Python", "FastAPI"]
    assert parsed.payload.likely_fit_level == "Strong"
    assert parsed.payload.resume_improvements == ["Add Docker evidence", "strengthen deployment stories"]
    assert parsed.payload.ats_improvements == []
    assert parsed.payload.interview_focus == ["Explain scaling tradeoffs"]


def test_job_analysis_schema_normalizes_nested_and_overlong_skill_lists(caplog):
    caplog.set_level(logging.INFO)
    logger = logging.getLogger("tests.job_analysis_schema_normalization")

    parsed = validate_ai_output(
        result={
            "summary": "Strong frontend role fit.",
            "seniority": "mid",
            "role_type": "frontend",
            "req_skills": [
                ["TypeScript", "React"],
                "Next.js, React Native",
                "Redux Toolkit",
                "TanStack Query",
                "Orval",
            ],
            "nice_skills": ["Shadcn/ui", "GitFlow"],
            "responsibilities": ["Build product interfaces", "Integrate APIs"],
            "prep": ["Review state management tradeoffs"],
            "learn": ["Practice React Native basics"],
            "gaps": ["React Native"],
            "resume": ["Highlight frontend ownership"],
            "interview": ["Explain architecture"],
            "projects": ["Build a demo app"],
        },
        schema=JobAnalysisAIOutput,
        operation="job_analysis",
        logger=logger,
    )

    assert parsed.payload.req_skills == [
        "TypeScript",
        "React",
        "Next.js",
        "React Native",
        "Redux Toolkit",
    ]


def test_run_structured_ai_call_retries_after_schema_failure(monkeypatch):
    monkeypatch.setattr(
        ai_module,
        "_ai_circuit_breaker",
        AICircuitBreaker(
            config=CircuitBreakerConfig(max_retries=0, initial_backoff_ms=0, max_backoff_ms=0),
            sleep_func=lambda _seconds: None,
        ),
    )

    calls: list[dict[str, object]] = []

    def flaky_structured_call(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return {"gaps": ["React Native"], "interview": ["Explain architecture"], "projects": ["Build a demo app"]}
        return dspy.Prediction(
            summary="Strong frontend role fit.",
            seniority="mid",
            role_type="frontend",
            req_skills=["TypeScript", "React"],
            nice_skills=["Next.js"],
            responsibilities=["Build product interfaces"],
            prep=["Review state management tradeoffs"],
            learn=["Practice React Native basics"],
            gaps=["React Native"],
            resume=["Highlight frontend ownership"],
            interview=["Explain architecture"],
            projects=["Build a demo app"],
        )

    executor = ThreadPoolExecutor(max_workers=1)
    try:
        parsed = ai_module.run_structured_ai_call(
            schema=JobAnalysisAIOutput,
            executor=executor,
            timeout_seconds=5,
            operation="job_analysis",
            logger=logging.getLogger("tests.structured_retry"),
            callable_=flaky_structured_call,
            lm_max_tokens=500,
            retry_lm_max_tokens=300,
            attempt_kwargs_builder_with_exception=lambda attempt, previous_exception: {
                "model": ai_module.use_provider_fallback_model(attempt + (1 if previous_exception else 0), previous_exception),
            },
        )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    assert parsed.payload.summary == "Strong frontend role fit."
    assert len(calls) == 2
    assert calls[0]["model"] == ai_module.get_settings().dspy_model
    assert calls[1]["model"] == ai_module.get_settings().dspy_provider_fallback_model


def test_cover_letter_generation_skips_cached_fallback_template(monkeypatch):
    service = CoverLetterService()
    service.generator = lambda **_kwargs: SimpleNamespace(
        cover_letter=(
            "Dear Acme team,\n\n"
            "I have led FastAPI and SQL delivery for backend products, including API reliability improvements and clearer operational workflows across production systems.\n\n"
            "That background would let me contribute quickly to this role while staying grounded in real, measurable experience.\n\n"
            "Thank you for your time and consideration."
        )
    )

    job = SimpleNamespace(
        id=1,
        title="Backend Engineer",
        company="Acme",
        clean_description="Python FastAPI SQL APIs and backend reliability.",
    )
    cv = SimpleNamespace(
        id=7,
        summary="Backend engineer focused on Python systems.",
        library_summary="Backend engineer with Python and FastAPI delivery.",
        clean_text="Built FastAPI services and SQL workflows with measurable impact.",
    )

    monkeypatch.setattr(cover_letter_module.crud, "get_job_for_user", lambda session, user_id, job_id: job)
    monkeypatch.setattr(cover_letter_module.crud, "get_cv_for_user", lambda session, user_id, cv_id: cv)
    monkeypatch.setattr(
        cover_letter_module.crud,
        "get_cached_cover_letter",
        lambda **_kwargs: (
            "Dear Acme team,\n\n"
            "I am excited to apply for the Backend Engineer role. My experience with Python, FastAPI aligns well with the kind of work described for this position.\n\n"
            "I have delivered practical work related to Python, FastAPI, and I would bring a clear, collaborative, and execution-focused approach from day one.\n\n"
            "Thank you for your time and consideration."
        ),
    )
    monkeypatch.setattr(cover_letter_module.crud, "update_job_cover_letter", lambda **_kwargs: None)

    try:
        output = service.generate_cover_letter(
            session=object(),
            user=SimpleNamespace(id=123),
            job_id=job.id,
            selected_cv_id=cv.id,
        )
    finally:
        service._executor.shutdown(wait=False, cancel_futures=True)

    assert "measurable experience" in output


def test_job_analysis_fallback_for_frontend_role_stays_role_specific():
    description = """
    Acerca del Rol
    Como desarrollador TypeScript/React, seras responsable de construir y optimizar nuestras aplicaciones moviles y de escritorio.
    Colaboraras con Producto, UX/UI y Backend para garantizar interfaces fluidas, seguras y de alto rendimiento.

    Responsabilidades
    Crear y mantener aplicaciones con TypeScript y React / React Native.
    Conectar interfaces con APIs RESTful y servicios backend.
    Analizar, diagnosticar y corregir bugs en produccion.

    Habilidades requeridas
    2+ anos con TypeScript y React.
    Experiencia con Context API, Redux Toolkit o TanStack Query.
    Conocimiento de SOLID y Clean Architecture.
    Dominio de Git y GitFlow.
    """

    service = JobAnalyzerService()
    try:
        payload = service._build_fallback_analysis_payload(
            title="Desarrollador TypeScript/React",
            company="Prueba Local",
            cleaned_description=description,
            language="spanish",
        )
    finally:
        service._executor.shutdown(wait=False, cancel_futures=True)

    all_text = " ".join(
        [
            payload.summary,
            *payload.required_skills,
            *payload.responsibilities,
            *payload.how_to_prepare,
            *payload.portfolio_project_ideas,
        ]
    ).lower()

    assert "typescript" in all_text
    assert "react" in all_text
    assert "retool" not in all_text
