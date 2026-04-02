from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.database import get_session
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.match import CVJobMatchRead
from app.services.cv_library_service import get_cv_library_service


router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[CVJobMatchRead])
def list_matches(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[CVJobMatchRead]:
    return get_cv_library_service().list_matches(session, current_user)


@router.get("/{match_id}", response_model=CVJobMatchRead)
def get_match(
    match_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CVJobMatchRead:
    return get_cv_library_service().get_match(session, current_user, match_id)
