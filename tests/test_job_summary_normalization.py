from app.services.cv_library_service import _build_match_explanation
from app.services.job_analyzer import _normalize_list, _normalize_summary_text


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


def test_cv_fallback_can_include_rewrite_ready_bullets():
    from app.services.cv_analyzer import CvAnalyzerService

    service = CvAnalyzerService()
    try:
        response = service._build_fallback_analysis(
            job_title="Backend Engineer",
            job_description="Python FastAPI SQL Docker observability backend APIs.",
            cv_text="Built Python APIs and improved SQL workflows in production.",
            language="english",
        )
    finally:
        service._executor.shutdown(wait=False, cancel_futures=True)

    assert isinstance(response.rewritten_bullets, list)
    assert len(response.rewritten_bullets) >= 1
