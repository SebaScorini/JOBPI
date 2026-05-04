from __future__ import annotations

from sqlmodel import Session

from app.db import crud
from app.models import InterviewSession


class InterviewRepository:
    """Data access boundary for interview session workflows."""

    def create_session(
        self,
        session: Session,
        *,
        user_id: int,
        job_id: int,
        cv_id: int,
        session_type: str,
        language: str,
        questions: list[dict],
        summary: dict | None = None,
    ) -> InterviewSession:
        return crud.create_interview_session(
            session,
            user_id=user_id,
            job_id=job_id,
            cv_id=cv_id,
            session_type=session_type,
            language=language,
            questions=questions,
            summary=summary,
        )

    def get_session_for_user(self, session: Session, *, user_id: int, session_id: int) -> InterviewSession | None:
        return crud.get_interview_session_for_user(session, user_id, session_id)

    def list_sessions_for_user(
        self,
        session: Session,
        *,
        user_id: int,
        job_id: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[InterviewSession], int]:
        return crud.get_interview_sessions_for_user(
            session,
            user_id,
            job_id=job_id,
            limit=limit,
            offset=offset,
        )

    def update_answers(self, session: Session, *, interview_session: InterviewSession, answers: list[dict]) -> InterviewSession:
        return crud.update_interview_session_answers(session, interview_session, answers)

    def update_evaluations(
        self,
        session: Session,
        *,
        interview_session: InterviewSession,
        evaluations: list[dict],
    ) -> InterviewSession:
        return crud.update_interview_session_evaluations(session, interview_session, evaluations)

    def update_summary(
        self,
        session: Session,
        *,
        interview_session: InterviewSession,
        summary: dict | None,
        overall_score: float | None = None,
        status: str | None = None,
    ) -> InterviewSession:
        return crud.update_interview_session_summary(
            session,
            interview_session,
            summary,
            overall_score=overall_score,
            status=status,
        )
