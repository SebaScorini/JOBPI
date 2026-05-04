from __future__ import annotations

from datetime import datetime

from sqlmodel import Session

from app.db import crud
from app.models import JobAnalysis


class JobRepository:
    """Data access boundary for job analysis persistence operations."""

    def find_matching_analysis(
        self,
        session: Session,
        *,
        user_id: int,
        title: str,
        company: str,
        clean_description: str,
    ) -> JobAnalysis | None:
        return crud.get_matching_job_analysis(
            session,
            user_id=user_id,
            title=title,
            company=company,
            clean_description=clean_description,
        )

    def list_for_user(
        self,
        session: Session,
        *,
        user_id: int,
        limit: int,
        offset: int,
        is_saved: bool | None,
    ) -> tuple[list[JobAnalysis], int]:
        return crud.get_jobs_for_user(
            session,
            user_id,
            limit=limit,
            offset=offset,
            is_saved=is_saved,
        )

    def get_for_user(self, session: Session, *, user_id: int, job_id: int) -> JobAnalysis | None:
        return crud.get_job_for_user(session, user_id, job_id)

    def get_by_id(self, session: Session, *, job_id: int) -> JobAnalysis | None:
        return crud.get_job_by_id(session, job_id)

    def create_analysis(
        self,
        session: Session,
        *,
        user_id: int,
        title: str,
        company: str,
        description: str,
        clean_description: str,
        analysis_result: dict[str, object],
    ) -> JobAnalysis:
        return crud.create_job_analysis(
            session,
            user_id=user_id,
            title=title,
            company=company,
            description=description,
            clean_description=clean_description,
            analysis_result=analysis_result,
        )

    def update_analysis_result(
        self,
        session: Session,
        *,
        job: JobAnalysis,
        analysis_result: dict[str, object],
    ) -> JobAnalysis:
        return crud.update_job_analysis_result(session, job, analysis_result)

    def delete(self, session: Session, *, job: JobAnalysis) -> None:
        crud.delete_job(session, job)

    def update_status(
        self,
        session: Session,
        *,
        job: JobAnalysis,
        status_value: str,
        applied_date: datetime | None,
    ) -> JobAnalysis:
        return crud.update_job_status(session, job, status_value, applied_date)

    def update_notes(self, session: Session, *, job: JobAnalysis, notes: str | None) -> JobAnalysis:
        return crud.update_job_notes(session, job, notes)

    def update_saved(self, session: Session, *, job: JobAnalysis, is_saved: bool) -> JobAnalysis:
        return crud.update_job_saved(session, job, is_saved)

    def update_cover_letter(
        self,
        session: Session,
        *,
        job: JobAnalysis,
        cv_id: int,
        language: str,
        cover_letter: str,
    ) -> JobAnalysis:
        return crud.update_job_cover_letter(
            session=session,
            job=job,
            cv_id=cv_id,
            language=language,
            cover_letter=cover_letter,
        )
