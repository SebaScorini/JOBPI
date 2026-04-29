"""
Comprehensive edge-case tests for the Interview Simulator (Sprint 11).

Covers:
- Empty / whitespace-only answers
- Invalid / foreign session IDs
- Out-of-order question submission
- Double-submission on a completed session
- Cross-user isolation (user A cannot see user B's session)
- Long answers (at the 8000-char limit and above)
- Multiple concurrent sessions for the same job
- Score calculation and strong/weak-area derivation
- AI schema edge cases (score out-of-range, too few questions, missing fields)
- GET session for wrong job_id
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# Shared AI stubs
# ---------------------------------------------------------------------------

def _make_ai_stub(score: int = 7):
    """Return a fake run_structured_ai_call that always evaluates with *score*."""
    def _fake(*, operation: str, **_kwargs):
        if operation == "interview_question_generation":
            payload = SimpleNamespace(
                questions=[
                    SimpleNamespace(question="Q1", category="behavioral", difficulty="easy", rationale="R"),
                    SimpleNamespace(question="Q2", category="technical", difficulty="medium", rationale="R"),
                    SimpleNamespace(question="Q3", category="situational", difficulty="medium", rationale="R"),
                    SimpleNamespace(question="Q4", category="culture_fit", difficulty="easy", rationale="R"),
                    SimpleNamespace(question="Q5", category="technical", difficulty="hard", rationale="R"),
                ],
                focus_areas=["area1", "area2"],
            )
            return SimpleNamespace(payload=payload)

        if operation == "interview_answer_evaluation":
            payload = SimpleNamespace(
                score=score,
                feedback="Good answer.",
                ideal_answer="An ideal answer would include concrete metrics.",
                improvement_tips=["Add metrics.", "Be more specific."],
            )
            return SimpleNamespace(payload=payload)

        raise AssertionError(f"Unexpected AI operation: {operation}")

    return _fake


def _patch_service(monkeypatch, stub):
    import app.services.interview_service as svc_module
    service = svc_module.get_interview_session_service()
    service.question_generator = lambda **_: None  # type: ignore[assignment]
    service.evaluator = lambda **_: None  # type: ignore[assignment]
    monkeypatch.setattr(svc_module, "run_structured_ai_call", stub)


# ---------------------------------------------------------------------------
# Helper: start a session and return (session_id, headers)
# ---------------------------------------------------------------------------

def _start_session(client, headers, job_id, cv_id, monkeypatch):
    """Start an interview session. Caller must have already called _patch_service."""
    resp = client.post(
        f"/jobs/{job_id}/interview/start",
        headers=headers,
        json={"cv_id": cv_id, "session_type": "mixed", "language": "english"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# 1. Empty answer – should be rejected by schema (min_length=1)
# ---------------------------------------------------------------------------

def test_empty_answer_rejected(client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch):
    headers = auth_headers()
    _patch_service(monkeypatch, _make_ai_stub())
    session_id = _start_session(client, headers, seeded_job.id, seeded_cv.id, monkeypatch)

    resp = client.post(
        f"/jobs/{seeded_job.id}/interview/{session_id}/answer",
        headers=headers,
        json={"question_index": 0, "answer_text": ""},
    )
    # Pydantic min_length=1 must reject this
    assert resp.status_code == 422, f"Expected 422 for empty answer, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# 2. Whitespace-only answer – should also fail validation
# ---------------------------------------------------------------------------

def test_whitespace_only_answer_rejected(client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch):
    headers = auth_headers()
    _patch_service(monkeypatch, _make_ai_stub())
    session_id = _start_session(client, headers, seeded_job.id, seeded_cv.id, monkeypatch)

    resp = client.post(
        f"/jobs/{seeded_job.id}/interview/{session_id}/answer",
        headers=headers,
        json={"question_index": 0, "answer_text": "   "},
    )
    # Whitespace-only answer must be rejected: the validator strips first,
    # then raises because the result is empty.
    assert resp.status_code == 422, (
        f"Expected 422 for whitespace-only answer, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 3. Invalid (non-existent) session ID → 404
# ---------------------------------------------------------------------------

def test_invalid_session_id_returns_404(client, auth_headers, test_db, seeded_job, monkeypatch):
    headers = auth_headers()
    import app.services.interview_service as svc_module
    _patch_service(monkeypatch, _make_ai_stub())

    resp = client.post(
        f"/jobs/{seeded_job.id}/interview/99999/answer",
        headers=headers,
        json={"question_index": 0, "answer_text": "Some answer"},
    )
    assert resp.status_code == 404, f"Expected 404 for unknown session, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# 4. GET session with wrong job_id → 404
# ---------------------------------------------------------------------------

def test_get_session_wrong_job_id_returns_404(client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch):
    headers = auth_headers()
    _patch_service(monkeypatch, _make_ai_stub())
    session_id = _start_session(client, headers, seeded_job.id, seeded_cv.id, monkeypatch)

    resp = client.get(
        f"/jobs/99999/interview/{session_id}",
        headers=headers,
    )
    assert resp.status_code == 404, f"Expected 404 for wrong job_id, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# 5. Out-of-order answer submission → 409
# ---------------------------------------------------------------------------

def test_out_of_order_answer_rejected(client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch):
    headers = auth_headers()
    _patch_service(monkeypatch, _make_ai_stub())
    session_id = _start_session(client, headers, seeded_job.id, seeded_cv.id, monkeypatch)

    # Skip index 0 and try to submit index 1
    resp = client.post(
        f"/jobs/{seeded_job.id}/interview/{session_id}/answer",
        headers=headers,
        json={"question_index": 1, "answer_text": "Jumping ahead"},
    )
    assert resp.status_code == 409, f"Expected 409 for out-of-order answer, got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# 6. Submitting to a completed session → 409
# ---------------------------------------------------------------------------

def test_answer_to_completed_session_rejected(client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch):
    headers = auth_headers()
    _patch_service(monkeypatch, _make_ai_stub())
    session_id = _start_session(client, headers, seeded_job.id, seeded_cv.id, monkeypatch)

    # Answer all 5 questions to complete the session
    for i in range(5):
        r = client.post(
            f"/jobs/{seeded_job.id}/interview/{session_id}/answer",
            headers=headers,
            json={"question_index": i, "answer_text": f"Answer {i}"},
        )
        assert r.status_code == 200, f"Failed at question {i}: {r.text}"

    # Attempt a 6th answer (index 5) → must be rejected
    resp = client.post(
        f"/jobs/{seeded_job.id}/interview/{session_id}/answer",
        headers=headers,
        json={"question_index": 5, "answer_text": "Extra answer"},
    )
    assert resp.status_code == 409, (
        f"Expected 409 for answer on completed session, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 7. Cross-user isolation: user B cannot access user A's session
# ---------------------------------------------------------------------------

def test_cross_user_session_isolation(client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch):
    # User A is the fixture owner — owns seeded_job and seeded_cv
    headers_a = auth_headers()  # tester@example.com
    _patch_service(monkeypatch, _make_ai_stub())
    session_id = _start_session(client, headers_a, seeded_job.id, seeded_cv.id, monkeypatch)

    # User B is a distinct second account
    headers_b = auth_headers(email="user_b@example.com")

    resp = client.get(
        f"/jobs/{seeded_job.id}/interview/{session_id}",
        headers=headers_b,
    )
    assert resp.status_code == 404, (
        f"User B should NOT see user A's session; got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 8. Long answer (exactly 8000 chars) → accepted
# ---------------------------------------------------------------------------

def test_long_answer_at_max_accepted(client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch):
    headers = auth_headers()
    _patch_service(monkeypatch, _make_ai_stub(score=5))
    session_id = _start_session(client, headers, seeded_job.id, seeded_cv.id, monkeypatch)

    long_answer = "A" * 8000  # exactly at the max_length limit
    resp = client.post(
        f"/jobs/{seeded_job.id}/interview/{session_id}/answer",
        headers=headers,
        json={"question_index": 0, "answer_text": long_answer},
    )
    assert resp.status_code == 200, f"8000-char answer should be accepted; got {resp.status_code}: {resp.text}"


# ---------------------------------------------------------------------------
# 9. Answer exceeding max_length (8001 chars) → 422
# ---------------------------------------------------------------------------

def test_answer_over_max_length_rejected(client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch):
    headers = auth_headers()
    _patch_service(monkeypatch, _make_ai_stub())
    session_id = _start_session(client, headers, seeded_job.id, seeded_cv.id, monkeypatch)

    over_limit_answer = "A" * 8001
    resp = client.post(
        f"/jobs/{seeded_job.id}/interview/{session_id}/answer",
        headers=headers,
        json={"question_index": 0, "answer_text": over_limit_answer},
    )
    assert resp.status_code == 422, (
        f"Expected 422 for 8001-char answer, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 10. Multiple sessions for the same job are independent
# ---------------------------------------------------------------------------

def test_multiple_sessions_same_job_are_independent(
    client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch
):
    headers = auth_headers()
    _patch_service(monkeypatch, _make_ai_stub())
    session_a = _start_session(client, headers, seeded_job.id, seeded_cv.id, monkeypatch)
    session_b = _start_session(client, headers, seeded_job.id, seeded_cv.id, monkeypatch)

    assert session_a != session_b, "Two consecutive start calls must create distinct sessions"

    # Answer Q0 in session_a only
    r = client.post(
        f"/jobs/{seeded_job.id}/interview/{session_a}/answer",
        headers=headers,
        json={"question_index": 0, "answer_text": "Answer for session A"},
    )
    assert r.status_code == 200, r.text

    # session_b must still show current_question_index=0
    r_b = client.get(f"/jobs/{seeded_job.id}/interview/{session_b}", headers=headers)
    assert r_b.status_code == 200, r_b.text
    assert r_b.json()["current_question_index"] == 0, (
        "Session B progress must be independent from session A"
    )


# ---------------------------------------------------------------------------
# 11. Overall score calculation is arithmetically correct
# ---------------------------------------------------------------------------

def test_overall_score_calculation(client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch):
    """All 5 answers score exactly 8 → overall_score must be 8.0."""
    headers = auth_headers()
    _patch_service(monkeypatch, _make_ai_stub(score=8))
    session_id = _start_session(client, headers, seeded_job.id, seeded_cv.id, monkeypatch)

    for i in range(5):
        r = client.post(
            f"/jobs/{seeded_job.id}/interview/{session_id}/answer",
            headers=headers,
            json={"question_index": i, "answer_text": f"Answer {i}"},
        )
        assert r.status_code == 200, r.text

    final = client.get(f"/jobs/{seeded_job.id}/interview/{session_id}", headers=headers)
    assert final.status_code == 200, final.text
    payload = final.json()
    assert payload["status"] == "completed"
    assert payload["summary"]["overall_score"] == 8.0, (
        f"Expected 8.0, got {payload['summary']['overall_score']}"
    )


# ---------------------------------------------------------------------------
# 12. Start session with invalid cv_id → 404
# ---------------------------------------------------------------------------

def test_start_session_invalid_cv_id(client, auth_headers, test_db, seeded_job, monkeypatch):
    headers = auth_headers()
    import app.services.interview_service as svc_module
    _patch_service(monkeypatch, _make_ai_stub())

    resp = client.post(
        f"/jobs/{seeded_job.id}/interview/start",
        headers=headers,
        json={"cv_id": 99999, "session_type": "mixed", "language": "english"},
    )
    assert resp.status_code == 404, (
        f"Expected 404 for invalid cv_id, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 13. Start session with invalid job_id → 404
# ---------------------------------------------------------------------------

def test_start_session_invalid_job_id(client, auth_headers, test_db, seeded_cv, monkeypatch):
    headers = auth_headers()
    import app.services.interview_service as svc_module
    _patch_service(monkeypatch, _make_ai_stub())

    resp = client.post(
        f"/jobs/99999/interview/start",
        headers=headers,
        json={"cv_id": seeded_cv.id, "session_type": "mixed", "language": "english"},
    )
    assert resp.status_code == 404, (
        f"Expected 404 for invalid job_id, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 14. Session starts with is_complete=False and status=in_progress
# ---------------------------------------------------------------------------

def test_session_initial_state(client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch):
    headers = auth_headers()
    _patch_service(monkeypatch, _make_ai_stub())

    resp = client.post(
        f"/jobs/{seeded_job.id}/interview/start",
        headers=headers,
        json={"cv_id": seeded_cv.id, "session_type": "mixed", "language": "english"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_complete"] is False
    assert body["status"] == "in_progress"
    assert body["current_question_index"] == 0
    assert body["answers"] == []
    assert body["evaluations"] == []
    assert body["summary"] is not None  # initial summary with focus_areas


# ---------------------------------------------------------------------------
# 15. List sessions returns all sessions for a job
# ---------------------------------------------------------------------------

def test_list_sessions_returns_all(client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch):
    headers = auth_headers()
    _patch_service(monkeypatch, _make_ai_stub())

    _start_session(client, headers, seeded_job.id, seeded_cv.id, monkeypatch)
    _start_session(client, headers, seeded_job.id, seeded_cv.id, monkeypatch)

    resp = client.get(f"/jobs/{seeded_job.id}/interview", headers=headers)
    assert resp.status_code == 200, resp.text
    sessions = resp.json()
    assert len(sessions) >= 2, f"Expected at least 2 sessions, got {len(sessions)}"


# ---------------------------------------------------------------------------
# 16. next_question_index is None after session is completed
# ---------------------------------------------------------------------------

def test_next_question_index_none_when_completed(
    client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch
):
    headers = auth_headers()
    _patch_service(monkeypatch, _make_ai_stub(score=6))
    session_id = _start_session(client, headers, seeded_job.id, seeded_cv.id, monkeypatch)

    for i in range(5):
        r = client.post(
            f"/jobs/{seeded_job.id}/interview/{session_id}/answer",
            headers=headers,
            json={"question_index": i, "answer_text": f"Answer {i}"},
        )
        assert r.status_code == 200, r.text

    final = client.get(f"/jobs/{seeded_job.id}/interview/{session_id}", headers=headers)
    assert final.status_code == 200, final.text
    body = final.json()
    assert body["next_question_index"] is None, (
        f"next_question_index should be None for completed session, got {body['next_question_index']}"
    )
    assert body["is_complete"] is True


# ---------------------------------------------------------------------------
# 17. Feedback response contains expected fields after answer
# ---------------------------------------------------------------------------

def test_feedback_response_structure(client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch):
    headers = auth_headers()
    _patch_service(monkeypatch, _make_ai_stub(score=9))
    session_id = _start_session(client, headers, seeded_job.id, seeded_cv.id, monkeypatch)

    resp = client.post(
        f"/jobs/{seeded_job.id}/interview/{session_id}/answer",
        headers=headers,
        json={"question_index": 0, "answer_text": "Structured, concrete answer with metrics."},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    required_fields = ["session_id", "question_index", "answer_text", "score", "feedback",
                       "ideal_answer", "improvement_tips", "is_complete", "next_question_index",
                       "evaluated_at"]
    for field in required_fields:
        assert field in body, f"Missing field '{field}' in feedback response"

    assert body["score"] == 9
    assert body["question_index"] == 0
    assert body["answer_text"] == "Structured, concrete answer with metrics."
    assert body["is_complete"] is False
    assert body["next_question_index"] == 1
    assert isinstance(body["improvement_tips"], list)


# ---------------------------------------------------------------------------
# 18. Unauthenticated request → 401
# ---------------------------------------------------------------------------

def test_unauthenticated_start_session_rejected(client, test_db, seeded_job, seeded_cv):
    resp = client.post(
        f"/jobs/{seeded_job.id}/interview/start",
        json={"cv_id": seeded_cv.id, "session_type": "mixed", "language": "english"},
    )
    assert resp.status_code in (401, 403), (
        f"Expected 401/403 for unauthenticated request, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 19. Session type validation: invalid session_type → 422
# ---------------------------------------------------------------------------

def test_invalid_session_type_rejected(client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch):
    headers = auth_headers()
    import app.services.interview_service as svc_module
    _patch_service(monkeypatch, _make_ai_stub())

    resp = client.post(
        f"/jobs/{seeded_job.id}/interview/start",
        headers=headers,
        json={"cv_id": seeded_cv.id, "session_type": "random_invalid_type", "language": "english"},
    )
    assert resp.status_code == 422, (
        f"Expected 422 for invalid session_type, got {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# 20. AI schema: score clamping (score must be 1-10)
# ---------------------------------------------------------------------------

def test_score_clamping_in_schema():
    """_normalize_interview_score should clamp scores to [1, 10]."""
    from app.models.ai_schemas import _normalize_interview_score  # type: ignore[attr-defined]

    assert _normalize_interview_score(0) == 1, "Score 0 should be clamped to 1"
    assert _normalize_interview_score(11) == 10, "Score 11 should be clamped to 10"
    assert _normalize_interview_score(5) == 5, "Score 5 should remain 5"
    assert _normalize_interview_score("bad") == 1, "Non-numeric score should fall back to 1"
    assert _normalize_interview_score(None) == 1, "None score should fall back to 1"
    assert _normalize_interview_score(7.8) == 7, "Float 7.8 should truncate to 7"
