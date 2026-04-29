from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.core.config import get_settings
from app.core.rate_limit import RateLimitPolicy, enforce_rate_limit
from app.db.database import get_session
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.interview import InterviewAnswerSubmit, InterviewFeedbackRead, InterviewSessionCreate, InterviewSessionRead


router = APIRouter(prefix="/jobs/{job_id}/interview", tags=["interviews"])


def _get_interview_session_service():
    from app.services.interview_service import get_interview_session_service

    return get_interview_session_service()


@router.post("/start", response_model=InterviewSessionRead)
def start_interview_session(
    request: Request,
    job_id: int,
    payload: InterviewSessionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> InterviewSessionRead:
    settings = get_settings()
    enforce_rate_limit(
        request=request,
        user=current_user,
        policy=RateLimitPolicy(
            name="interview_start",
            limit=settings.job_analyze_limit,
            window_seconds=settings.job_analyze_window_seconds,
        ),
    )
    return _get_interview_session_service().start_session(session, current_user, job_id, payload)


@router.post("/{session_id}/answer", response_model=InterviewFeedbackRead)
def submit_interview_answer(
    request: Request,
    job_id: int,
    session_id: int,
    payload: InterviewAnswerSubmit,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> InterviewFeedbackRead:
    settings = get_settings()
    enforce_rate_limit(
        request=request,
        user=current_user,
        policy=RateLimitPolicy(
            name="interview_answer",
            limit=settings.job_analyze_limit,
            window_seconds=settings.job_analyze_window_seconds,
        ),
    )
    return _get_interview_session_service().submit_answer(session, current_user, job_id, session_id, payload)


@router.get("/{session_id}", response_model=InterviewSessionRead)
def get_interview_session(
    job_id: int,
    session_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> InterviewSessionRead:
    return _get_interview_session_service().get_session(session, current_user, job_id, session_id)


@router.get("", response_model=list[InterviewSessionRead])
def list_interview_sessions(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[InterviewSessionRead]:
    return _get_interview_session_service().list_sessions(session, current_user, job_id)