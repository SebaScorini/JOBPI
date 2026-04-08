from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.core.pagination import PaginationParams, build_paginated_response
from app.db.database import get_session
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.match import CVJobMatchRead, MatchListResponse
from app.services.cv_library_service import get_cv_library_service


router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=MatchListResponse)
def list_matches(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> MatchListResponse:
    params = PaginationParams(limit=limit, offset=offset)
    matches, total = get_cv_library_service().list_matches(
        session,
        current_user,
        limit=params.limit,
        offset=params.offset,
    )
    return build_paginated_response(matches, total, params.limit, params.offset)


@router.get("/{match_id}", response_model=CVJobMatchRead)
def get_match(
    match_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CVJobMatchRead:
    return get_cv_library_service().get_match(session, current_user, match_id)
