from app.services.job_analyzer import _normalize_summary_text


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
