from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from app.schemas.cv import CvAnalysisResponse
from app.services.cv_analyzer import CvAnalyzerService, _refine_cv_analysis_response
from app.services.cv_library_service import CvLibraryService
from app.services.job_preprocessing import build_cv_context, build_job_context, clean_description
from app.services.pdf_extractor import preprocess_cv_text

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "ai_quality"


def _read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8").strip()


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _build_display_result(response: CvAnalysisResponse) -> object:
    fake_match = SimpleNamespace(
        id=1,
        user_id=1,
        cv_id=1,
        job_id=1,
        fit_level=response.likely_fit_level,
        fit_summary=response.fit_summary,
        strengths=response.strengths,
        missing_skills=response.missing_skills,
        recommended=False,
        created_at=datetime.now(timezone.utc),
    )
    service = CvLibraryService.__new__(CvLibraryService)
    return CvLibraryService._serialize_match_detail(service, fake_match, response, 0.42, "english")


def test_fixture_preprocessing_keeps_job_and_cv_context():
    job_text = _read_fixture("backend_job.txt")
    cv_text = _read_fixture("cv_backend_strong.txt")

    job_context = build_job_context(clean_description(job_text), title="Backend Engineer", company="Northstar Analytics")
    cv_summary = _first_non_empty_line(cv_text)
    cv_context = build_cv_context(
        preprocess_cv_text(cv_text),
        summary=cv_summary,
        library_summary=cv_summary,
    )

    assert "FastAPI" in job_context
    assert "PostgreSQL" in job_context
    assert "## Job Title" in job_context
    assert "## CV Summary" in cv_context
    assert "## CV Content" in cv_context
    assert "Python" in cv_context
    assert "Docker" in cv_context


def test_fixture_prompt_keeps_long_summary_and_structured_inputs():
    job_text = _read_fixture("backend_job.txt")
    cv_text = _read_fixture("cv_backend_strong.txt")
    captured: dict[str, object] = {}

    class CaptureAnalyzer:
        def __call__(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                fit_summary=(
                    "The CV shows direct backend delivery with FastAPI, PostgreSQL, and observability. "
                    "The strongest evidence is the workflow platform work, while the main gap is deeper cloud scope. "
                    "The candidate also shows product collaboration, API reliability work, and Docker-based delivery habits. "
                    "Together those signals make the profile a credible fit for the role, especially if the team values production ownership. "
                    "The combination of stable API delivery, practical debugging, and measurable workflow impact gives a reviewer concrete reasons to trust the fit."
                ),
                strengths=[
                    "FastAPI services for workflow platforms",
                    "PostgreSQL design and SQL query work",
                    "Observability and incident diagnosis",
                    "Dockerized delivery environments",
                ],
                missing_skills=[
                    "Broader cloud deployment evidence",
                    "More explicit AI ranking system depth",
                ],
                likely_fit_level="Strong",
                resume_improvements=["Move the matching-system project higher in the resume."],
                ats_improvements=["Repeat FastAPI and PostgreSQL wording where truthful."],
                recruiter_improvements=["Quantify incident reduction and workflow impact."],
                rewritten_bullets=["Built FastAPI APIs that supported hiring workflow matching and status updates."],
                interview_focus=["Explain matching workflow tradeoffs."],
                next_steps=["Prepare a metrics-backed story about API reliability."],
            )

    service = CvAnalyzerService()
    service.analyzer = CaptureAnalyzer()

    try:
        response = service.analyze(
            job_title="Backend Engineer",
            job_description=job_text,
            cv_text=cv_text,
            cv_summary=_first_non_empty_line(cv_text),
            cv_library_summary=_first_non_empty_line(cv_text),
        )
    finally:
        service._executor.shutdown(wait=False, cancel_futures=True)

    assert "## Job Title" in str(captured["job_description"])
    assert "## CV Summary" in str(captured["cv_text"])
    assert "FastAPI" in str(captured["job_description"])
    assert "Docker" in str(captured["cv_text"])
    assert len(response.fit_summary) > 420
    assert "workflow platform" in response.fit_summary


def test_strong_and_weak_fixtures_produce_distinct_frontend_output():
    job_text = _read_fixture("backend_job.txt")
    strong_cv_text = _read_fixture("cv_backend_strong.txt")
    weak_cv_text = _read_fixture("cv_backend_weak.txt")

    class FixtureDrivenAnalyzer:
        def __call__(self, **kwargs):
            cv_text = str(kwargs.get("cv_text", ""))
            if "FastAPI" in cv_text and "PostgreSQL" in cv_text:
                return SimpleNamespace(
                    fit_summary="Strong fit: the CV shows FastAPI, PostgreSQL, observability, and Docker evidence.",
                    strengths=["FastAPI services", "PostgreSQL and SQL", "Observability", "Docker delivery"],
                    missing_skills=["Broader cloud deployment scope", "More AI product evidence"],
                    likely_fit_level="Strong",
                    resume_improvements=["Move the matching project higher in the resume."],
                    ats_improvements=["Repeat exact FastAPI and PostgreSQL wording where truthful."],
                    recruiter_improvements=["Quantify incident reduction and delivery speed."],
                    rewritten_bullets=["Built FastAPI APIs for workflow matching and reporting."],
                    interview_focus=["Discuss system design tradeoffs."],
                    next_steps=["Prepare a backend metrics story."],
                )

            return SimpleNamespace(
                fit_summary="Moderate fit: the CV shows web delivery, but backend evidence is thin.",
                strengths=["JavaScript and React delivery", "Documentation support"],
                missing_skills=["Deep FastAPI evidence", "PostgreSQL architecture examples"],
                likely_fit_level="Moderate",
                resume_improvements=["Add a backend project with APIs and SQL."],
                ats_improvements=["Surface backend keywords only where they are truthful."],
                recruiter_improvements=["Show measurable ownership beyond support work."],
                rewritten_bullets=["Supported web delivery and helped coordinate releases for a small team."],
                interview_focus=["Explain any backend systems you owned."],
                next_steps=["Build one concrete backend project with metrics."],
            )

    service = CvAnalyzerService()
    service.analyzer = FixtureDrivenAnalyzer()

    try:
        strong_response = service.analyze(
            job_title="Backend Engineer",
            job_description=job_text,
            cv_text=strong_cv_text,
            cv_summary=_first_non_empty_line(strong_cv_text),
            cv_library_summary=_first_non_empty_line(strong_cv_text),
        )
        weak_response = service.analyze(
            job_title="Backend Engineer",
            job_description=job_text,
            cv_text=weak_cv_text,
            cv_summary=_first_non_empty_line(weak_cv_text),
            cv_library_summary=_first_non_empty_line(weak_cv_text),
        )
    finally:
        service._executor.shutdown(wait=False, cancel_futures=True)

    strong_display = _build_display_result(_refine_cv_analysis_response(strong_response))
    weak_display = _build_display_result(_refine_cv_analysis_response(weak_response))

    assert strong_display.why_this_cv != weak_display.why_this_cv
    assert "FastAPI" in strong_display.why_this_cv
    assert "React" in weak_display.why_this_cv or "JavaScript" in weak_display.why_this_cv
