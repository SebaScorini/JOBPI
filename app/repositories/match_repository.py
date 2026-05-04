from __future__ import annotations

from sqlmodel import Session

from app.db import crud
from app.models import CV, CVJobMatch, JobAnalysis


class MatchRepository:
    """Data access boundary for matching and comparison workflows."""

    def get_job_for_user(self, session: Session, user_id: int, job_id: int) -> JobAnalysis | None:
        return crud.get_job_for_user(session, user_id, job_id)

    def get_cv_for_user(self, session: Session, user_id: int, cv_id: int) -> CV | None:
        return crud.get_cv_for_user(session, user_id, cv_id)

    def get_cvs_for_user(self, session: Session, user_id: int, *, limit: int, offset: int) -> tuple[list[CV], int]:
        return crud.get_cvs_for_user(session, user_id, limit=limit, offset=offset)

    def get_match_for_user_by_cv_and_job(self, session: Session, user_id: int, cv_id: int, job_id: int) -> CVJobMatch | None:
        return crud.get_match_for_user_by_cv_and_job(session, user_id, cv_id, job_id)

    def create_match(
        self,
        session: Session,
        *,
        user_id: int,
        cv_id: int,
        job_id: int,
        fit_level: str,
        fit_summary: str,
        strengths: list[str],
        missing_skills: list[str],
        recommended: bool = False,
        result: dict | None = None,
    ) -> CVJobMatch:
        return crud.create_match(
            session,
            user_id=user_id,
            cv_id=cv_id,
            job_id=job_id,
            fit_level=fit_level,
            fit_summary=fit_summary,
            strengths=strengths,
            missing_skills=missing_skills,
            recommended=recommended,
            result=result,
        )

    def replace_recommended_match(self, session: Session, match: CVJobMatch) -> CVJobMatch:
        return crud.replace_recommended_match(session, match)

    def get_matches_for_user(self, session: Session, user_id: int, *, limit: int, offset: int) -> tuple[list[CVJobMatch], int]:
        return crud.get_matches_for_user(session, user_id, limit=limit, offset=offset)

    def get_match_for_user(self, session: Session, user_id: int, match_id: int) -> CVJobMatch | None:
        return crud.get_match_for_user(session, user_id, match_id)

    def update_match_analysis(
        self,
        session: Session,
        match: CVJobMatch,
        *,
        fit_level: str,
        fit_summary: str,
        strengths: list[str],
        missing_skills: list[str],
        result: dict | None = None,
    ) -> CVJobMatch:
        return crud.update_match_analysis(
            session,
            match,
            fit_level=fit_level,
            fit_summary=fit_summary,
            strengths=strengths,
            missing_skills=missing_skills,
            result=result,
        )
