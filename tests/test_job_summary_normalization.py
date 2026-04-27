from app.services.cv_library_service import _build_match_explanation
from app.services.job_analyzer import _normalize_list, _normalize_summary_text
from app.services.cv_analyzer import _refine_cv_analysis_response
from app.schemas.cv import CvAnalysisResponse
from app.schemas.job import JobAnalysisPayload
from app.services.job_analyzer import _refine_job_analysis_payload


def test_normalize_summary_prefers_complete_sentences():
    text = (
        "This role owns backend platform reliability and API architecture across multiple teams. "
        "It also requires strong collaboration with product, data, and infrastructure partners. "
        "Candidates should additionally drive long-term modernization initiatives for legacy services."
    )

    normalized = _normalize_summary_text(text, 190)

    assert normalized == (
        "This role owns backend platform reliability and API architecture across multiple teams. "
        "It also requires strong collaboration with product, data, and infrastructure partners."
    )


def test_normalize_summary_avoids_half_sentence_cutoffs():
    text = (
        "This role focuses on backend platform reliability, API design, cloud operations, stakeholder "
        "alignment, observability, incident response, and scalable delivery across a distributed team "
        "working on business-critical systems with high uptime expectations."
    )

    normalized = _normalize_summary_text(text, 120)

    assert len(normalized) <= 120
    assert "expectations" not in normalized
    assert normalized[-1].isalnum()


def test_normalize_summary_removes_dangling_parenthesis_fragment():
    text = "This role values frontend frameworks (e.g., React, Angular) and close collaboration with product."

    normalized = _normalize_summary_text(text, 43)

    assert normalized
    assert not normalized.endswith("(")
    assert "(e.g" not in normalized.lower()


def test_normalize_list_item_removes_truncated_eg_fragment():
    normalized = _normalize_list(["Experience with JavaScript frameworks (e.g."])

    assert len(normalized) == 1
    assert not normalized[0].endswith("(")
    assert "(e.g" not in normalized[0].lower()


def test_normalize_list_item_removes_dangling_closing_parenthesis_fragment():
    normalized = _normalize_list(["Improved model quality with 4% accuracy gain).,"])

    assert len(normalized) == 1
    assert normalized[0].endswith("gain")
    assert not normalized[0].endswith(")")


def test_normalize_list_keeps_more_actionable_detail_per_item():
    normalized = _normalize_list(
        [
            "Highlight backend API ownership with measurable latency, reliability, and delivery improvements across recent roles and flagship projects."
        ]
    )

    assert len(normalized) == 1
    assert "measurable latency" in normalized[0]
    assert "flagship projects" in normalized[0]


def test_build_match_explanation_includes_strengths_and_main_gaps():
    explanation = _build_match_explanation(
        fit_summary="The CV shows credible backend delivery evidence for this role.",
        strengths=[
            "Strong FastAPI and Python delivery in production environments",
            "Clear SQL and PostgreSQL ownership with measurable impact",
            "Evidence of API performance improvements",
        ],
        missing_skills=[
            "Limited evidence of Docker and container orchestration",
            "No explicit observability ownership examples",
        ],
        improvement_suggestions=[
            "Add one bullet showing containerized deployment ownership",
            "Call out monitoring, logging, or incident-response work",
        ],
        language="english",
    )

    why_this_cv = explanation["why_this_cv"]

    assert "Key strengths" in why_this_cv
    assert "Main gaps" in why_this_cv
    assert "FastAPI and Python" in why_this_cv
    assert "Docker and container orchestration" in why_this_cv


def test_build_match_explanation_generates_richer_improvement_suggestions():
    explanation = _build_match_explanation(
        fit_summary="The CV shows credible backend delivery evidence for this role.",
        strengths=[
            "Strong FastAPI and Python delivery in production environments",
        ],
        missing_skills=[
            "Limited evidence of Docker and container orchestration",
            "No explicit observability ownership examples",
        ],
        improvement_suggestions=[],
        language="english",
    )

    suggestions = explanation["suggested_improvements"]

    assert len(suggestions) >= 4
    assert any("project or bullet" in item.lower() for item in suggestions)
    assert any("metrics" in item.lower() for item in suggestions)
    assert any(
        "professional summary" in item.lower() or "primary fit signal" in item.lower()
        for item in suggestions
    )
    assert any("exact wording" in item.lower() for item in suggestions)


def test_refine_cv_analysis_response_reduces_cross_section_repetition():
    response = CvAnalysisResponse(
        fit_summary="Strong fit with good backend evidence and one visible Docker gap.",
        strengths=["Strong FastAPI delivery in production systems"],
        missing_skills=["Missing clear Docker deployment evidence"],
        likely_fit_level="Strong",
        resume_improvements=[
            "Add one bullet with Docker deployment ownership and measurable production impact",
            "Add one bullet with Docker deployment ownership and measurable production impact",
        ],
        ats_improvements=[
            "Use exact Docker deployment wording from the posting in relevant experience",
            "Use exact Docker deployment wording from the posting in relevant experience",
        ],
        recruiter_improvements=[
            "Quantify Docker deployment impact with reliability or delivery metrics",
            "Quantify Docker deployment impact with reliability or delivery metrics",
        ],
        rewritten_bullets=[
            "Led FastAPI service delivery and improved backend reliability by 30% across production workflows."
        ],
        interview_focus=[
            "Prepare to explain Docker deployment tradeoffs in production"
        ],
        next_steps=[
            "Update the CV with Docker deployment evidence before applying",
            "Update the CV with Docker deployment evidence before applying",
        ],
    )

    refined = _refine_cv_analysis_response(response)

    assert len(refined.resume_improvements) <= 1
    assert len(refined.ats_improvements) <= 1
    assert len(refined.recruiter_improvements) <= 1
    assert len(refined.next_steps) <= 1
    assert refined.resume_improvements or refined.ats_improvements or refined.recruiter_improvements


def test_refine_cv_analysis_response_filters_generic_missing_skills():
    response = CvAnalysisResponse(
        fit_summary="Moderate fit with good backend experience but a few visible gaps.",
        strengths=["Strong FastAPI delivery in production systems"],
        missing_skills=[
            "More experience",
            "Add Docker deployment bullet",
            "Limited evidence of Docker production ownership",
            "No explicit observability ownership examples",
        ],
        likely_fit_level="Moderate",
        resume_improvements=["Add Docker deployment bullet"],
        ats_improvements=[],
        recruiter_improvements=[],
        rewritten_bullets=[],
        interview_focus=[],
        next_steps=[],
    )

    refined = _refine_cv_analysis_response(response)

    assert "More experience" not in refined.missing_skills
    assert "Add Docker deployment bullet" not in refined.missing_skills
    assert "Limited evidence of Docker production ownership" in refined.missing_skills
    assert "No explicit observability ownership examples" in refined.missing_skills


def test_refine_job_analysis_payload_reduces_cross_section_repetition():
    payload = JobAnalysisPayload(
        summary="Backend platform role focused on API delivery and production reliability.",
        seniority="mid",
        role_type="backend",
        required_skills=["Python", "FastAPI", "Docker"],
        nice_to_have_skills=["Kubernetes"],
        responsibilities=["Own backend API delivery across production systems"],
        how_to_prepare=[
            "Prepare examples of backend API delivery across production systems",
            "Prepare examples of backend API delivery across production systems",
        ],
        learning_path=[
            "Study backend API delivery tradeoffs across production systems",
        ],
        missing_skills=["Clear Docker production ownership evidence"],
        resume_tips=[
            "Show backend API delivery across production systems with measurable impact",
            "Show backend API delivery across production systems with measurable impact",
        ],
        interview_tips=[
            "Discuss backend API delivery tradeoffs in production systems",
            "Discuss backend API delivery tradeoffs in production systems",
        ],
        portfolio_project_ideas=[
            "Build a backend API platform demo with production-style observability and Docker delivery",
            "Build a backend API platform demo with production-style observability and Docker delivery",
        ],
    )

    refined = _refine_job_analysis_payload(payload)

    assert len(refined.how_to_prepare) <= 1
    assert len(refined.resume_tips) <= 1
    assert len(refined.interview_tips) <= 1
    assert len(refined.portfolio_project_ideas) <= 1
