from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.core.config import get_settings
from app.core.rate_limit import RateLimitPolicy, enforce_rate_limit
from app.core.security import create_access_token, hash_password, verify_password
from app.db.crud import create_user, get_user_by_email
from app.db.database import get_session
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.auth import TokenResponse, UserRead, UserRegisterRequest


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    request: Request,
    payload: UserRegisterRequest,
    session: Session = Depends(get_session),
) -> UserRead:
    settings = get_settings()
    enforce_rate_limit(
        request=request,
        policy=RateLimitPolicy(
            name="auth_register",
            limit=settings.auth_register_limit,
            window_seconds=settings.auth_window_seconds,
        ),
        email=payload.email,
    )

    if "@" not in payload.email or payload.email.startswith("@") or payload.email.endswith("@"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A valid email address is required.",
        )

    existing = get_user_by_email(session, payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that email already exists.",
        )

    try:
        user = create_user(
            session,
            email=payload.email,
            hashed_password=hash_password(payload.password),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> TokenResponse:
    settings = get_settings()
    enforce_rate_limit(
        request=request,
        policy=RateLimitPolicy(
            name="auth_login",
            limit=settings.auth_login_limit,
            window_seconds=settings.auth_window_seconds,
        ),
        email=form_data.username,
    )

    user = get_user_by_email(session, form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user.",
        )

    # Create JWT with user ID as the subject
    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
