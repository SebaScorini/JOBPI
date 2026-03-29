from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.database import get_session
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.job import (
    CoverLetterGenerateRequest,
    CoverLetterGenerateResponse,
    JobAnalysisRequest,
    JobNotesUpdateRequest,
    JobRead,
    JobStatusUpdateRequest,
)
from app.schemas.match import CVComparisonResponse, CVCompareRequest, CVJobMatchDetailRead, CVMatchRequest
from app.services.cover_letter_service import get_cover_letter_service
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
    return get_cv_library_service().match_job_to_cv(
        session,
        current_user,
        job_id,
        payload.cv_id,
        payload.language,
    )


@router.post("/{job_id}/compare-cvs", response_model=CVComparisonResponse)
def compare_cvs_for_job(
    job_id: int,
    payload: CVCompareRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CVComparisonResponse:
    return get_cv_library_service().compare_cvs_for_job(
        session,
        current_user,
        job_id,
        payload.cv_id_a,
        payload.cv_id_b,
        payload.language,
    )


@router.post("/{job_id}/cover-letter", response_model=CoverLetterGenerateResponse)
def generate_cover_letter(
    job_id: int,
    payload: CoverLetterGenerateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CoverLetterGenerateResponse:
    generated_cover_letter = get_cover_letter_service().generate_cover_letter(
        session=session,
        user=current_user,
        job_id=job_id,
        selected_cv_id=payload.selected_cv_id,
        language=payload.language,
    )
    return CoverLetterGenerateResponse(generated_cover_letter=generated_cover_letter)
