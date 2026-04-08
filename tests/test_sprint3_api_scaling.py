from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine

from app.db import crud
from app.db.database import get_session
from app.dependencies.auth import get_current_user
from app.main import create_app
from app.models import User


def _build_client():
    tmp_dir = Path.cwd() / ".tmp-tests"
    tmp_dir.mkdir(exist_ok=True)
    db_path = tmp_dir / f"sprint3-{uuid4().hex}.db"
    engine = create_engine(f"sqlite:///{db_path.resolve().as_posix()}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    user = crud.create_user(session, "sprint3@example.com", "hashed-password")

    app = create_app()

    def session_override():
        yield session

    def current_user_override() -> User:
        return user

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_current_user] = current_user_override

    client = TestClient(app)
    return client, session, user, app, engine, db_path


def _teardown_client(client: TestClient, session: Session, app, engine, db_path: Path) -> None:
    client.close()
    session.close()
    app.dependency_overrides.clear()
    engine.dispose()
    if db_path.exists():
        db_path.unlink()


def test_cvs_list_supports_pagination_search_and_tags():
    client, session, user, app, engine, db_path = _build_client()
    try:
        crud.create_cv(
            session,
            user_id=user.id,
            filename="backend.pdf",
            display_name="Backend Resume",
            raw_text="backend raw",
            clean_text="backend clean",
            summary="Backend summary",
            library_summary="Backend library summary",
            tags=["python", "backend"],
        )
        crud.create_cv(
            session,
            user_id=user.id,
            filename="frontend.pdf",
            display_name="Frontend Resume",
            raw_text="frontend raw",
            clean_text="frontend clean",
            summary="Frontend summary",
            library_summary="Frontend library summary",
            tags=["react", "frontend"],
        )

        response = client.get("/cvs?limit=1&offset=0&search=resume&tags=python")

        assert response.status_code == 200
        payload = response.json()
        assert list(payload.keys()) == ["items", "pagination"]
        assert len(payload["items"]) == 1
        assert payload["items"][0]["display_name"] == "Backend Resume"
        assert payload["pagination"]["total"] == 1
        assert payload["pagination"]["limit"] == 1
        assert payload["pagination"]["offset"] == 0
        assert payload["pagination"]["has_more"] is False
    finally:
        _teardown_client(client, session, app, engine, db_path)


def test_jobs_and_matches_list_return_paginated_shape():
    client, session, user, app, engine, db_path = _build_client()
    try:
        job = crud.create_job_analysis(
            session,
            user_id=user.id,
            title="Backend Engineer",
            company="Acme",
            description="Job description",
            clean_description="backend api python",
            analysis_result={
                "summary": "summary",
                "seniority": "mid",
                "role_type": "backend",
                "required_skills": ["python"],
                "nice_to_have_skills": [],
                "responsibilities": [],
                "how_to_prepare": [],
                "learning_path": [],
                "missing_skills": [],
                "resume_tips": [],
                "interview_tips": [],
                "portfolio_project_ideas": [],
            },
        )
        cv = crud.create_cv(
            session,
            user_id=user.id,
            filename="resume.pdf",
            display_name="Resume",
            raw_text="raw",
            clean_text="clean",
            summary="summary",
            library_summary="library",
            tags=[],
        )
        crud.create_match(
            session,
            user_id=user.id,
            cv_id=cv.id,
            job_id=job.id,
            fit_level="strong",
            fit_summary="Strong fit",
            strengths=["Python"],
            missing_skills=[],
        )

        jobs_response = client.get("/jobs?limit=10&offset=0")
        matches_response = client.get("/matches?limit=10&offset=0")

        assert jobs_response.status_code == 200
        assert matches_response.status_code == 200
        assert "pagination" in jobs_response.json()
        assert "pagination" in matches_response.json()
        assert jobs_response.json()["pagination"]["total"] == 1
        assert matches_response.json()["pagination"]["total"] == 1
    finally:
        _teardown_client(client, session, app, engine, db_path)


def test_bulk_tag_and_bulk_delete_work():
    client, session, user, app, engine, db_path = _build_client()
    try:
        cv1 = crud.create_cv(
            session,
            user_id=user.id,
            filename="one.pdf",
            display_name="One",
            raw_text="raw1",
            clean_text="clean1",
            summary="summary1",
            library_summary="library1",
            tags=["existing"],
        )
        cv2 = crud.create_cv(
            session,
            user_id=user.id,
            filename="two.pdf",
            display_name="Two",
            raw_text="raw2",
            clean_text="clean2",
            summary="summary2",
            library_summary="library2",
            tags=[],
        )

        bulk_tag = client.post(
            "/cvs/bulk-tag",
            json={"cv_ids": [cv1.id, cv2.id], "tags": ["python", "backend"]},
        )
        assert bulk_tag.status_code == 200
        assert bulk_tag.json() == {"updated": 2, "deleted": 0, "failed": 0}

        refreshed_one = crud.get_cv_for_user(session, user.id, cv1.id)
        refreshed_two = crud.get_cv_for_user(session, user.id, cv2.id)
        assert refreshed_one is not None and set(refreshed_one.tags) == {"existing", "python", "backend"}
        assert refreshed_two is not None and set(refreshed_two.tags) == {"python", "backend"}

        bulk_delete = client.post("/cvs/bulk-delete", json={"cv_ids": [cv1.id, cv2.id]})
        assert bulk_delete.status_code == 200
        assert bulk_delete.json() == {"updated": 0, "deleted": 2, "failed": 0}
        remaining, total = crud.get_cvs_for_user(session, user.id)
        assert total == 0
        assert remaining == []
    finally:
        _teardown_client(client, session, app, engine, db_path)


def test_standardized_errors_include_code_and_trace_id():
    client, session, user, app, engine, db_path = _build_client()
    try:
        response = client.get("/cvs/999")

        assert response.status_code == 404
        payload = response.json()
        assert payload["error"]["code"] == "ERR_CV_NOT_FOUND"
        assert payload["error"]["message"] == "CV not found."
        assert payload["error"]["request_id"]
        assert payload["error"]["timestamp"]
    finally:
        _teardown_client(client, session, app, engine, db_path)


def test_request_size_limit_returns_413():
    client, session, user, app, engine, db_path = _build_client()
    try:
        oversized_body = "x" * ((10 * 1024 * 1024) + 1)
        response = client.post(
            "/auth/register",
            content=oversized_body,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 413
        payload = response.json()
        assert payload["error"]["code"] == "ERR_PAYLOAD_TOO_LARGE"
    finally:
        _teardown_client(client, session, app, engine, db_path)
