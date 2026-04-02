from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.core.config import get_settings
from app.core.rate_limit import RateLimitPolicy, enforce_rate_limit
from app.core.validation import reject_oversized_request
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
    request: Request,
    payload: JobAnalysisRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    settings = get_settings()
    is_trusted_user = settings.should_bypass_user_limits(current_user.email)
    if not is_trusted_user:
        reject_oversized_request(
            request=request,
            max_bytes=(settings.max_job_description_chars * 4) + 4096,
            detail=(
                "Request body is too large. "
                f"Job description must be {settings.max_job_description_chars} characters or fewer."
            ),
        )
    enforce_rate_limit(
        request=request,
        user=current_user,
        policy=RateLimitPolicy(
            name="job_analyze",
            limit=settings.job_analyze_limit,
            window_seconds=settings.job_analyze_window_seconds,
        ),
    )
    if not is_trusted_user and len(payload.description) > settings.max_job_description_chars:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Job description must be {settings.max_job_description_chars} characters or fewer."
            ),
        )
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
    request: Request,
    job_id: int,
    payload: CVMatchRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CVJobMatchDetailRead:
    settings = get_settings()
    enforce_rate_limit(
        request=request,
        user=current_user,
        policy=RateLimitPolicy(
            name="match_cvs",
            limit=settings.match_cvs_limit,
            window_seconds=settings.match_cvs_window_seconds,
        ),
    )
    return get_cv_library_service().match_job_to_cv(
        session,
        current_user,
        job_id,
        payload.cv_id,
        payload.language,
        payload.regenerate,
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
    request: Request,
    job_id: int,
    payload: CoverLetterGenerateRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CoverLetterGenerateResponse:
    settings = get_settings()
    enforce_rate_limit(
        request=request,
        user=current_user,
        policy=RateLimitPolicy(
            name="cover_letter",
            limit=settings.cover_letter_limit,
            window_seconds=settings.cover_letter_window_seconds,
        ),
    )
    generated_cover_letter = get_cover_letter_service().generate_cover_letter(
        session=session,
        user=current_user,
        job_id=job_id,
        selected_cv_id=payload.selected_cv_id,
        language=payload.language,
        regenerate=payload.regenerate,
    )
    return CoverLetterGenerateResponse(generated_cover_letter=generated_cover_letter)
