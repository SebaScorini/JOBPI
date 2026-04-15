from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.core.logging import bind_user_context
from app.core.security import decode_access_token
from app.core.supabase_auth import SupabaseAuthError, is_supabase_token, verify_supabase_token
from app.db.database import get_session
from app.db.crud import get_or_create_user_by_supabase_id, get_user_by_email, get_user_by_id
from app.models import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    """Authenticate via Supabase JWT or legacy app JWT (bridge period).

    Supabase tokens are detected by the ``aud=authenticated`` claim.  If
    detected, the token is verified against the Supabase JWT secret and the
    user is resolved (or auto-created) via ``supabase_user_id``.

    Legacy tokens are decoded with the app's own secret key as before.
    """
    # --- Supabase Auth path ---
    if is_supabase_token(token):
        try:
            payload = verify_supabase_token(token)
        except SupabaseAuthError:
            raise _unauthorized()

        supabase_uid: str = payload["sub"]
        email: str | None = payload.get("email")

        user = get_or_create_user_by_supabase_id(
            session,
            supabase_user_id=supabase_uid,
            email=email,
        )
        if user is None or not user.is_active:
            raise _unauthorized()

        request.state.user_id = str(user.id)
        request.state.user_email = user.email
        bind_user_context(user.id)
        return user

    # --- Legacy JWT path (bridge period – will be removed) ---
    payload = decode_access_token(token)
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise _unauthorized()

    user: User | None  # type: ignore[no-redef]
    if subject.isdigit():
        user = get_user_by_id(session, int(subject))
    else:
        user = get_user_by_email(session, subject)

    if user is None or not user.is_active:
        raise _unauthorized()

    request.state.user_id = str(user.id)
    request.state.user_email = user.email
    bind_user_context(user.id)
    return user


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
