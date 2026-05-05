from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlmodel import Session

from app.core.config import get_settings
from app.core.rate_limit import RateLimitPolicy, enforce_rate_limit
from app.db.database import get_session
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.linkedin import (
    ColdOutreachRead,
    ColdOutreachRequest,
    LinkedInProfileRead,
    LinkedInProfileRequest,
)


router = APIRouter(prefix="/linkedin", tags=["linkedin"])


def _get_linkedin_service():
    from app.services.linkedin_service import get_linkedin_service

    return get_linkedin_service()


def _preflight_linkedin_generation(request: Request, current_user: User) -> None:
    settings = get_settings()
    enforce_rate_limit(
        request=request,
        user=current_user,
        policy=RateLimitPolicy(
            name="job_analyze",
            limit=settings.job_analyze_limit,
            window_seconds=settings.job_analyze_window_seconds,
        ),
    )


@router.post("/profile", response_model=LinkedInProfileRead)
def generate_linkedin_profile(
    request: Request,
    payload: LinkedInProfileRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> LinkedInProfileRead:
    _preflight_linkedin_generation(request, current_user)
    return _get_linkedin_service().generate_linkedin_profile(
        session=session,
        user=current_user,
        cv_id=payload.cv_id,
        job_ids=payload.job_ids,
        language=payload.language,
        regenerate=payload.regenerate,
    )


@router.get("/profile", response_model=LinkedInProfileRead | None)
def get_cached_linkedin_profile(
    response: Response,
    cv_id: int = Query(..., gt=0),
    job_ids: list[int] | None = Query(default=None, max_length=5),
    language: str = "english",
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> LinkedInProfileRead | None:
    cached = _get_linkedin_service().get_cached_linkedin_profile(
        session=session,
        user=current_user,
        cv_id=cv_id,
        job_ids=job_ids or [],
        language=language,  # type: ignore[arg-type]
    )
    if cached is None:
        response.status_code = status.HTTP_204_NO_CONTENT
    return cached


@router.post("/outreach", response_model=ColdOutreachRead)
def generate_cold_outreach(
    request: Request,
    payload: ColdOutreachRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ColdOutreachRead:
    _preflight_linkedin_generation(request, current_user)
    return _get_linkedin_service().generate_cold_outreach(
        session=session,
        user=current_user,
        job_id=payload.job_id,
        cv_id=payload.cv_id,
        hiring_manager_name=payload.hiring_manager_name,
        language=payload.language,
        regenerate=payload.regenerate,
    )


@router.get("/outreach", response_model=ColdOutreachRead | None)
def get_cached_cold_outreach(
    response: Response,
    job_id: int = Query(..., gt=0),
    cv_id: int = Query(..., gt=0),
    hiring_manager_name: str | None = Query(default=None, max_length=120),
    language: str = "english",
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ColdOutreachRead | None:
    cached = _get_linkedin_service().get_cached_cold_outreach(
        session=session,
        user=current_user,
        job_id=job_id,
        cv_id=cv_id,
        hiring_manager_name=hiring_manager_name,
        language=language,  # type: ignore[arg-type]
    )
    if cached is None:
        response.status_code = status.HTTP_204_NO_CONTENT
    return cached


