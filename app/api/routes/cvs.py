from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel import Session

from app.db.database import get_session
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.cv import CVDetailRead, CVRead
from app.services.cv_library_service import get_cv_library_service


router = APIRouter(prefix="/cvs", tags=["cvs"])

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024


@router.post("/upload", response_model=CVRead, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    display_name: str = Form(..., min_length=1, max_length=200),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CVRead:
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file must be a PDF.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="PDF file must be under 5 MB.",
        )

    service = get_cv_library_service()
    try:
        return service.upload_cv(
            session=session,
            user=current_user,
            display_name=display_name,
            filename=file.filename or "resume.pdf",
            file_bytes=file_bytes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[CVRead])
def list_cvs(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[CVRead]:
    return get_cv_library_service().list_cvs(session, current_user)


@router.get("/{cv_id}", response_model=CVDetailRead)
def get_cv(
    cv_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CVDetailRead:
    return get_cv_library_service().get_cv(session, current_user, cv_id)


@router.delete("/{cv_id}")
def delete_cv(
    cv_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    get_cv_library_service().delete_cv(session, current_user, cv_id)
    return {"ok": True}
