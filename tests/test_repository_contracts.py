from __future__ import annotations

from types import SimpleNamespace

from app.repositories.cv_library_repository import CvLibraryRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.job_repository import JobRepository
from app.repositories.match_repository import MatchRepository


def test_job_repository_update_cover_letter_delegates_to_crud(monkeypatch):
    repo = JobRepository()
    session = object()
    job = SimpleNamespace(id=11)
    expected = SimpleNamespace(id=11, generated_cover_letter="Tailored cover letter")
    captured: dict[str, object] = {}

    def fake_update_job_cover_letter(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        "app.repositories.job_repository.crud.update_job_cover_letter",
        fake_update_job_cover_letter,
    )

    result = repo.update_cover_letter(
        session,
        job=job,
        cv_id=7,
        language="english",
        cover_letter="Tailored cover letter",
    )

    assert result is expected
    assert captured["session"] is session
    assert captured["job"] is job
    assert captured["cv_id"] == 7
    assert captured["language"] == "english"
    assert captured["cover_letter"] == "Tailored cover letter"


def test_interview_repository_create_session_delegates_to_crud(monkeypatch):
    repo = InterviewRepository()
    session = object()
    expected = SimpleNamespace(id=99)
    captured: dict[str, object] = {}

    def fake_create_interview_session(
        session_arg,
        user_id,
        job_id,
        cv_id,
        session_type,
        language,
        questions,
        summary,
    ):
        captured.update(
            {
                "session": session_arg,
                "user_id": user_id,
                "job_id": job_id,
                "cv_id": cv_id,
                "session_type": session_type,
                "language": language,
                "questions": questions,
                "summary": summary,
            }
        )
        return expected

    monkeypatch.setattr(
        "app.repositories.interview_repository.crud.create_interview_session",
        fake_create_interview_session,
    )

    result = repo.create_session(
        session,
        user_id=1,
        job_id=2,
        cv_id=3,
        session_type="mixed",
        language="english",
        questions=[{"question": "Q1"}],
        summary={"focus_areas": ["backend"]},
    )

    assert result is expected
    assert captured == {
        "session": session,
        "user_id": 1,
        "job_id": 2,
        "cv_id": 3,
        "session_type": "mixed",
        "language": "english",
        "questions": [{"question": "Q1"}],
        "summary": {"focus_areas": ["backend"]},
    }


def test_interview_repository_update_summary_delegates_to_crud(monkeypatch):
    repo = InterviewRepository()
    session = object()
    interview_session = SimpleNamespace(id=7)
    expected = SimpleNamespace(id=7, status="completed")
    captured: dict[str, object] = {}

    def fake_update_interview_session_summary(
        session_arg,
        interview_session_arg,
        summary,
        *,
        overall_score=None,
        status=None,
    ):
        captured.update(
            {
                "session": session_arg,
                "interview_session": interview_session_arg,
                "summary": summary,
                "overall_score": overall_score,
                "status": status,
            }
        )
        return expected

    monkeypatch.setattr(
        "app.repositories.interview_repository.crud.update_interview_session_summary",
        fake_update_interview_session_summary,
    )

    result = repo.update_summary(
        session,
        interview_session=interview_session,
        summary={"overall_score": 8.2},
        overall_score=8.2,
        status="completed",
    )

    assert result is expected
    assert captured == {
        "session": session,
        "interview_session": interview_session,
        "summary": {"overall_score": 8.2},
        "overall_score": 8.2,
        "status": "completed",
    }


def test_cv_library_repository_create_cv_delegates_to_crud(monkeypatch):
    repo = CvLibraryRepository()
    session = object()
    expected = SimpleNamespace(id=3)
    captured: dict[str, object] = {}

    def fake_create_cv(
        session_arg,
        user_id,
        filename,
        display_name,
        raw_text,
        clean_text,
        summary,
        library_summary,
        tags,
    ):
        captured.update(
            {
                "session": session_arg,
                "user_id": user_id,
                "filename": filename,
                "display_name": display_name,
                "raw_text": raw_text,
                "clean_text": clean_text,
                "summary": summary,
                "library_summary": library_summary,
                "tags": tags,
            }
        )
        return expected

    monkeypatch.setattr(
        "app.repositories.cv_library_repository.crud.create_cv",
        fake_create_cv,
    )

    result = repo.create_cv(
        session,
        user_id=22,
        filename="resume.pdf",
        display_name="Primary Resume",
        raw_text="raw",
        clean_text="clean",
        summary="short summary",
        library_summary="library summary",
        tags=["python", "backend"],
    )

    assert result is expected
    assert captured == {
        "session": session,
        "user_id": 22,
        "filename": "resume.pdf",
        "display_name": "Primary Resume",
        "raw_text": "raw",
        "clean_text": "clean",
        "summary": "short summary",
        "library_summary": "library summary",
        "tags": ["python", "backend"],
    }


def test_cv_library_repository_get_filtered_cvs_for_user_delegates_to_crud(monkeypatch):
    repo = CvLibraryRepository()
    session = object()
    expected = ([SimpleNamespace(id=1)], 1)
    captured: dict[str, object] = {}

    def fake_get_filtered_cvs_for_user(
        session_arg,
        user_id,
        *,
        search,
        tags,
        limit,
        offset,
    ):
        captured.update(
            {
                "session": session_arg,
                "user_id": user_id,
                "search": search,
                "tags": tags,
                "limit": limit,
                "offset": offset,
            }
        )
        return expected

    monkeypatch.setattr(
        "app.repositories.cv_library_repository.crud.get_filtered_cvs_for_user",
        fake_get_filtered_cvs_for_user,
    )

    result = repo.get_filtered_cvs_for_user(
        session,
        8,
        search="fastapi",
        tags=["backend"],
        limit=10,
        offset=5,
    )

    assert result is expected
    assert captured == {
        "session": session,
        "user_id": 8,
        "search": "fastapi",
        "tags": ["backend"],
        "limit": 10,
        "offset": 5,
    }


def test_match_repository_create_match_delegates_to_crud(monkeypatch):
    repo = MatchRepository()
    session = object()
    expected = SimpleNamespace(id=17)
    captured: dict[str, object] = {}

    def fake_create_match(
        session_arg,
        user_id,
        cv_id,
        job_id,
        fit_level,
        fit_summary,
        strengths,
        missing_skills,
        recommended=False,
        result=None,
    ):
        captured.update(
            {
                "session": session_arg,
                "user_id": user_id,
                "cv_id": cv_id,
                "job_id": job_id,
                "fit_level": fit_level,
                "fit_summary": fit_summary,
                "strengths": strengths,
                "missing_skills": missing_skills,
                "recommended": recommended,
                "result": result,
            }
        )
        return expected

    monkeypatch.setattr(
        "app.repositories.match_repository.crud.create_match",
        fake_create_match,
    )

    result = repo.create_match(
        session,
        user_id=4,
        cv_id=5,
        job_id=6,
        fit_level="high",
        fit_summary="Strong fit",
        strengths=["Python"],
        missing_skills=["Kubernetes"],
        recommended=True,
        result={"score": 87},
    )

    assert result is expected
    assert captured == {
        "session": session,
        "user_id": 4,
        "cv_id": 5,
        "job_id": 6,
        "fit_level": "high",
        "fit_summary": "Strong fit",
        "strengths": ["Python"],
        "missing_skills": ["Kubernetes"],
        "recommended": True,
        "result": {"score": 87},
    }


def test_match_repository_update_match_analysis_delegates_to_crud(monkeypatch):
    repo = MatchRepository()
    session = object()
    match = SimpleNamespace(id=23)
    expected = SimpleNamespace(id=23, fit_level="medium")
    captured: dict[str, object] = {}

    def fake_update_match_analysis(
        session_arg,
        match_arg,
        fit_level,
        fit_summary,
        strengths,
        missing_skills,
        result=None,
    ):
        captured.update(
            {
                "session": session_arg,
                "match": match_arg,
                "fit_level": fit_level,
                "fit_summary": fit_summary,
                "strengths": strengths,
                "missing_skills": missing_skills,
                "result": result,
            }
        )
        return expected

    monkeypatch.setattr(
        "app.repositories.match_repository.crud.update_match_analysis",
        fake_update_match_analysis,
    )

    result = repo.update_match_analysis(
        session,
        match,
        fit_level="medium",
        fit_summary="Needs stronger depth",
        strengths=["SQL"],
        missing_skills=["Leadership"],
        result={"notes": "refresh"},
    )

    assert result is expected
    assert captured == {
        "session": session,
        "match": match,
        "fit_level": "medium",
        "fit_summary": "Needs stronger depth",
        "strengths": ["SQL"],
        "missing_skills": ["Leadership"],
        "result": {"notes": "refresh"},
    }
