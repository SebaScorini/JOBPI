"""Pytest configuration and reusable fixtures for JOBPI tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Keep tests hermetic even when the local .env points at production-style Postgres.
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = f"sqlite:///{(project_root / 'test_jobpi.db').as_posix()}"

from app.core.security import hash_password  # noqa: E402
from app.db import crud  # noqa: E402
from app.db.database import get_session  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import User  # noqa: E402


@pytest.fixture
def test_db():
    tmp_dir = project_root / ".tmp-tests"
    tmp_dir.mkdir(exist_ok=True)
    db_path = tmp_dir / f"jobpi-{uuid4().hex}.db"
    engine = create_engine(
        f"sqlite:///{db_path.resolve().as_posix()}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        if db_path.exists():
            db_path.unlink()


@pytest.fixture
def client(test_db: Session, monkeypatch: pytest.MonkeyPatch):
    import app.main as main_module

    monkeypatch.setattr(main_module, "ensure_database_schema", lambda: None)
    app = create_app()

    def session_override():
        yield test_db

    app.dependency_overrides[get_session] = session_override

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def create_user(test_db: Session):
    def _create_user(email: str = "tester@example.com", password: str = "ValidPass123") -> User:
        return crud.create_user(test_db, email=email, hashed_password=hash_password(password))

    return _create_user


@pytest.fixture
def auth_headers(client: TestClient):
    def _auth_headers(email: str = "tester@example.com", password: str = "ValidPass123") -> dict[str, str]:
        client.post(
            "/auth/register",
            json={"email": email, "password": password},
        )
        response = client.post(
            "/auth/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers


@pytest.fixture
def seeded_user(create_user):
    return create_user()


@pytest.fixture
def seeded_cv(test_db: Session, seeded_user: User):
    return crud.create_cv(
        test_db,
        user_id=seeded_user.id,
        filename="resume.pdf",
        display_name="Primary Resume",
        raw_text="Python FastAPI SQL delivery",
        clean_text="Python FastAPI SQL delivery",
        summary="Experienced backend engineer.",
        library_summary="Backend engineer focused on APIs and SQL systems.",
        tags=["python", "backend"],
    )


@pytest.fixture
def seeded_job(test_db: Session, seeded_user: User):
    return crud.create_job_analysis(
        test_db,
        user_id=seeded_user.id,
        title="Backend Engineer",
        company="Acme",
        description="Need Python FastAPI SQL APIs and testing experience." * 2,
        clean_description="Need Python FastAPI SQL APIs and testing experience." * 2,
        analysis_result={
            "summary": "Strong backend role.",
            "seniority": "mid",
            "role_type": "backend",
            "required_skills": ["Python", "FastAPI", "SQL"],
            "nice_to_have_skills": ["Docker"],
            "responsibilities": ["Build APIs"],
            "how_to_prepare": ["Review API design"],
            "learning_path": ["Practice testing"],
            "missing_skills": ["Docker"],
            "resume_tips": ["Highlight APIs"],
            "interview_tips": ["Explain SQL tradeoffs"],
            "portfolio_project_ideas": ["Build an API service"],
        },
    )
