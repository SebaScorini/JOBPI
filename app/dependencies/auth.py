from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.security import decode_access_token
from app.db.database import get_session
from app.db.crud import get_user_by_email, get_user_by_id
from app.models import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    payload = decode_access_token(token)
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise _unauthorized()

    user: User | None
    if subject.isdigit():
        user = get_user_by_id(session, int(subject))
    else:
        user = get_user_by_email(session, subject)

    if user is None or not user.is_active:
        raise _unauthorized()
    return user


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
