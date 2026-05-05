from __future__ import annotations

from types import SimpleNamespace

from fastapi import HTTPException


def _fake_structured_ai_call(*, operation: str, **_kwargs):
    if operation == "interview_question_generation":
        payload = SimpleNamespace(
            questions=[
                SimpleNamespace(question="Describe a time you improved a backend workflow.", category="behavioral", difficulty="medium", rationale="Tests evidence of ownership and impact."),
                SimpleNamespace(question="How would you debug a slow API endpoint?", category="technical", difficulty="medium", rationale="Checks practical troubleshooting depth."),
                SimpleNamespace(question="Tell me about a time you handled conflicting priorities.", category="situational", difficulty="easy", rationale="Evaluates prioritization under pressure."),
                SimpleNamespace(question="How do you work with product or design partners?", category="culture_fit", difficulty="easy", rationale="Checks collaboration style."),
                SimpleNamespace(question="Walk me through a system you designed end to end.", category="technical", difficulty="hard", rationale="Surfaces architecture and tradeoff thinking."),
            ],
            focus_areas=["backend ownership", "debugging", "cross-functional collaboration"],
        )
        return SimpleNamespace(payload=payload)

    if operation == "interview_answer_evaluation":
        question_text = ""
        builder = _kwargs.get("attempt_kwargs_builder_with_exception")
        if callable(builder):
            try:
                attempt_kwargs = builder(0, None)
            except TypeError:
                attempt_kwargs = builder(0)
            question_text = attempt_kwargs.get("question", "")
        score = 8 if "backend workflow" in question_text else 6
        payload = SimpleNamespace(
            score=score,
            feedback="Good structure, but the answer needs more concrete evidence and outcome detail.",
            ideal_answer="A strong answer would name the situation, the action you took, and the measurable result.",
            improvement_tips=["Add a specific metric.", "Tie the example back to the role requirements."],
        )
        return SimpleNamespace(payload=payload)

    raise AssertionError(f"Unexpected AI operation: {operation}")


def test_interview_session_flow(client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch):
    import app.services.interview_service as interview_service_module

    service = interview_service_module.get_interview_session_service()
    service.question_generator = lambda **_kwargs: None
    service.evaluator = lambda **_kwargs: None
    monkeypatch.setattr(interview_service_module, "run_structured_ai_call", _fake_structured_ai_call)

    headers = auth_headers()

    start_response = client.post(
        f"/jobs/{seeded_job.id}/interview/start",
        headers=headers,
        json={"cv_id": seeded_cv.id, "session_type": "mixed", "language": "english"},
    )

    assert start_response.status_code == 200, start_response.text
    start_payload = start_response.json()
    assert start_payload["status"] == "in_progress"
    assert len(start_payload["questions"]) == 5
    assert start_payload["summary"]["focus_areas"] == ["backend ownership", "debugging", "cross-functional collaboration"]

    session_id = start_payload["id"]

    first_answer = client.post(
        f"/jobs/{seeded_job.id}/interview/{session_id}/answer",
        headers=headers,
        json={"question_index": 0, "answer_text": "I improved the API workflow by removing repeated work and measuring the impact."},
    )
    assert first_answer.status_code == 200, first_answer.text
    first_feedback = first_answer.json()
    assert first_feedback["question_index"] == 0
    assert first_feedback["is_complete"] is False
    assert first_feedback["next_question_index"] == 1

    second_answer = client.post(
        f"/jobs/{seeded_job.id}/interview/{session_id}/answer",
        headers=headers,
        json={"question_index": 1, "answer_text": "I debugged the endpoint by tracing the slow query and validating the fix with metrics."},
    )
    assert second_answer.status_code == 200, second_answer.text
    second_feedback = second_answer.json()
    assert second_feedback["question_index"] == 1
    assert second_feedback["is_complete"] is False
    assert second_feedback["next_question_index"] == 2

    for index in range(2, 5):
        response = client.post(
            f"/jobs/{seeded_job.id}/interview/{session_id}/answer",
            headers=headers,
            json={
                "question_index": index,
                "answer_text": f"Answer {index} with enough role-specific evidence and a clear result.",
            },
        )
        assert response.status_code == 200, response.text

    final_response = client.get(
        f"/jobs/{seeded_job.id}/interview/{session_id}",
        headers=headers,
    )

    final_payload = final_response.json()
    assert final_payload["status"] == "completed"
    assert final_payload["current_question_index"] == 5
    assert final_payload["summary"]["overall_score"] == 6.4

    assert len(final_payload["answers"]) == 5
    assert len(final_payload["evaluations"]) == 5
    assert final_payload["summary"]["strong_areas"]


def test_interview_answer_submit_uses_fallback_when_ai_evaluation_fails(client, auth_headers, test_db, seeded_job, seeded_cv, monkeypatch):
    import app.services.interview_service as interview_service_module

    service = interview_service_module.get_interview_session_service()
    service.question_generator = lambda **_kwargs: None
    service.evaluator = lambda **_kwargs: None

    def failing_structured_ai_call(*, operation: str, **_kwargs):
        if operation == "interview_question_generation":
            return _fake_structured_ai_call(operation=operation, **_kwargs)
        raise RuntimeError("openrouter unavailable")

    monkeypatch.setattr(interview_service_module, "run_structured_ai_call", failing_structured_ai_call)

    headers = auth_headers()
    start_response = client.post(
        f"/jobs/{seeded_job.id}/interview/start",
        headers=headers,
        json={"cv_id": seeded_cv.id, "session_type": "mixed", "language": "english"},
    )
    assert start_response.status_code == 200, start_response.text
    session_id = start_response.json()["id"]

    answer_response = client.post(
        f"/jobs/{seeded_job.id}/interview/{session_id}/answer",
        headers=headers,
        json={"question_index": 0, "answer_text": "I improved the API workflow and measured the outcome."},
    )

    assert answer_response.status_code == 200, answer_response.text
    feedback = answer_response.json()
    assert feedback["question_index"] == 0
    assert feedback["answer_text"] == "I improved the API workflow and measured the outcome."
    assert feedback["feedback"].startswith("AI evaluation was unavailable")

    saved_session = client.get(
        f"/jobs/{seeded_job.id}/interview/{session_id}",
        headers=headers,
    )
    assert saved_session.status_code == 200, saved_session.text
    session_payload = saved_session.json()
    assert session_payload["status"] == "in_progress"
    assert session_payload["answers"][0]["answer_text"] == "I improved the API workflow and measured the outcome."