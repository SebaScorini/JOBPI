from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import Session

from app.core.config import get_settings
from app.core.pagination import PaginationParams, build_paginated_response
from app.core.rate_limit import RateLimitPolicy, enforce_rate_limit
from app.core.validation import reject_oversized_request
from app.db.database import get_session
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.job import (
    CoverLetterGenerateRequest,
    CoverLetterGenerateResponse,
    JobAnalysisRequest,
    JobDeleteResponse,
    JobListResponse,
    JobNotesUpdateRequest,
    JobRead,
    JobStatusUpdateRequest,
)
from app.schemas.match import CVComparisonResponse, CVCompareRequest, CVJobMatchDetailRead, CVMatchRequest
from app.services.cover_letter_service import get_cover_letter_service
from app.services.cv_library_service import get_cv_library_service
from app.services.job_analyzer import get_job_analyzer_service


router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_description_limit_message(limit: int) -> str:
    return (
        f"Job description is too long for a reliable analysis. Keep it under {limit} characters and "
        "paste only the most important details: responsibilities, required skills, tools/stack, seniority, "
        "and must-have qualifications."
    )


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
    analysis_input_limit = min(
        getattr(settings, "job_preprocess_target_chars", settings.max_job_description_chars),
        settings.max_job_description_chars,
    )
    if not is_trusted_user and len(payload.description) > analysis_input_limit:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=_job_description_limit_message(analysis_input_limit),
        )
    if not is_trusted_user and len(payload.description) > settings.max_job_description_chars:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Job description must be {settings.max_job_description_chars} characters or fewer."
            ),
        )
    return get_job_analyzer_service().analyze(payload, session=session, user=current_user)


@router.get("", response_model=JobListResponse)
def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    saved: bool | None = Query(default=None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> JobListResponse:
    params = PaginationParams(limit=limit, offset=offset)
    jobs, total = get_job_analyzer_service().list_jobs(
        session,
        current_user,
        limit=params.limit,
        offset=params.offset,
        is_saved=saved,
    )
    return build_paginated_response(jobs, total, params.limit, params.offset)


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    return get_job_analyzer_service().get_job(session, current_user, job_id)


@router.delete(
    "/{job_id}",
    response_model=JobDeleteResponse,
    summary="Delete a job",
    description="Deletes a job owned by the authenticated user.",
    responses={
        403: {"description": "The job belongs to a different user."},
        404: {"description": "The requested job was not found."},
    },
)
def delete_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> JobDeleteResponse:
    return get_job_analyzer_service().delete_job(session, current_user, job_id)


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


@router.patch("/{job_id}/toggle-saved", response_model=JobRead)
def toggle_job_saved(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    return get_job_analyzer_service().toggle_job_saved(session, current_user, job_id)


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
