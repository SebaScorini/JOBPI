from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.database import get_session
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.job import JobAnalysisRequest, JobNotesUpdateRequest, JobRead, JobStatusUpdateRequest
from app.schemas.match import CVJobMatchDetailRead, CVMatchRequest
from app.services.cv_library_service import get_cv_library_service
from app.services.job_analyzer import get_job_analyzer_service


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/analyze", response_model=JobRead)
def analyze_job(
    payload: JobAnalysisRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    return get_job_analyzer_service().analyze(payload, session=session, user=current_user)


@router.get("", response_model=list[JobRead])
def list_jobs(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[JobRead]:
    return get_job_analyzer_service().list_jobs(session, current_user)


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    return get_job_analyzer_service().get_job(session, current_user, job_id)


@router.patch("/{job_id}/status", response_model=JobRead)
def update_job_status(
    job_id: int,
    payload: JobStatusUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    return get_job_analyzer_service().update_job_status(
        session,
        current_user,
        job_id,
        payload.status,
        payload.applied_date,
    )


@router.patch("/{job_id}/notes", response_model=JobRead)
def update_job_notes(
    job_id: int,
    payload: JobNotesUpdateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    return get_job_analyzer_service().update_job_notes(session, current_user, job_id, payload.notes)


@router.post("/{job_id}/match-cvs", response_model=CVJobMatchDetailRead)
def match_job_to_cvs(
    job_id: int,
    payload: CVMatchRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CVJobMatchDetailRead:
    return get_cv_library_service().match_job_to_cv(session, current_user, job_id, payload.cv_id)
