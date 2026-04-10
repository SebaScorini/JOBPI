"""Lightweight local benchmark script for Sprint 6 reliability baselines."""

from __future__ import annotations

import statistics
import os
import sys
import time
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = f"sqlite:///{(PROJECT_ROOT / '.tmp-tests' / 'benchmark-bootstrap.db').as_posix()}"

from app.core.security import hash_password
from app.db import crud
from app.db.database import get_session
from app.main import create_app


def _build_client():
    tmp_dir = Path.cwd() / ".tmp-tests"
    tmp_dir.mkdir(exist_ok=True)
    db_path = tmp_dir / f"benchmark-{uuid4().hex}.db"
    engine = create_engine(
        f"sqlite:///{db_path.resolve().as_posix()}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    user = crud.create_user(session, "benchmark@example.com", hash_password("ValidPass123"))

    for index in range(25):
        crud.create_cv(
            session,
            user_id=user.id,
            filename=f"resume-{index}.pdf",
            display_name=f"Resume {index}",
            raw_text="Python FastAPI SQL testing",
            clean_text=f"Python FastAPI SQL testing {index}",
            summary="Backend profile",
            library_summary="Backend profile summary",
            tags=["python", "backend"] if index % 2 == 0 else ["testing"],
        )

    app = create_app()

    def session_override():
        yield session

    app.dependency_overrides[get_session] = session_override
    client = TestClient(app)
    return client, app, session, engine, db_path


def _teardown(client, app, session, engine, db_path: Path) -> None:
    client.close()
    app.dependency_overrides.clear()
    session.close()
    engine.dispose()
    if db_path.exists():
        db_path.unlink()


def _measure(label: str, operation, iterations: int = 10) -> tuple[str, float, float]:
    timings_ms: list[float] = []
    for _ in range(iterations):
        started_at = time.perf_counter()
        operation()
        timings_ms.append((time.perf_counter() - started_at) * 1000)

    average = statistics.mean(timings_ms)
    p95_index = max(0, min(len(timings_ms) - 1, round((len(timings_ms) - 1) * 0.95)))
    p95 = sorted(timings_ms)[p95_index]
    return label, round(average, 2), round(p95, 2)


def main() -> int:
    client, app, session, engine, db_path = _build_client()

    try:
        login_response = client.post(
            "/auth/login",
            data={"username": "benchmark@example.com", "password": "ValidPass123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        login_response.raise_for_status()
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        results = [
            _measure("GET /health", lambda: client.get("/health").raise_for_status()),
            _measure(
                "POST /auth/login",
                lambda: client.post(
                    "/auth/login",
                    data={"username": "benchmark@example.com", "password": "ValidPass123"},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                ).raise_for_status(),
            ),
            _measure(
                "GET /cvs?limit=20",
                lambda: client.get("/cvs?limit=20&offset=0", headers=headers).raise_for_status(),
            ),
            _measure(
                "GET /cvs search+tags",
                lambda: client.get("/cvs?limit=10&offset=0&search=Resume&tags=python", headers=headers).raise_for_status(),
            ),
        ]

        print("Sprint 6 local benchmark baselines (ms)")
        for label, avg_ms, p95_ms in results:
            print(f"- {label}: avg={avg_ms} p95={p95_ms}")

        return 0
    finally:
        _teardown(client, app, session, engine, db_path)


if __name__ == "__main__":
    raise SystemExit(main())
