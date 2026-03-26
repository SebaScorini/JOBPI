from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel import Session

from app.db.database import get_session
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.cv import CVDetailRead, CVRead, CVBatchUploadResponse, CVUploadResult
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


@router.post("/batch-upload", response_model=CVBatchUploadResponse, status_code=status.HTTP_201_CREATED)
async def batch_upload_cvs(
    files: list[UploadFile] = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CVBatchUploadResponse:
    """Upload multiple CV files at once. Processes each file independently."""
    
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided.",
        )

    service = get_cv_library_service()
    results: list[CVUploadResult] = []
    succeeded = 0
    failed = 0

    for file in files:
        try:
            # Validate file type
            if file.content_type not in ("application/pdf", "application/octet-stream"):
                results.append(
                    CVUploadResult(
                        filename=file.filename or "unknown",
                        success=False,
                        error="File must be a PDF.",
                    )
                )
                failed += 1
                continue

            # Read file and validate size
            file_bytes = await file.read()
            if len(file_bytes) > MAX_FILE_SIZE_BYTES:
                results.append(
                    CVUploadResult(
                        filename=file.filename or "unknown",
                        success=False,
                        error="PDF file must be under 5 MB.",
                    )
                )
                failed += 1
                continue

            # Use filename as display name (without extension)
            display_name = file.filename or "resume.pdf"
            if display_name.endswith(".pdf"):
                display_name = display_name[:-4]

            # Upload the CV
            cv = service.upload_cv(
                session=session,
                user=current_user,
                display_name=display_name.strip(),
                filename=file.filename or "resume.pdf",
                file_bytes=file_bytes,
            )
            results.append(
                CVUploadResult(
                    filename=file.filename or "resume.pdf",
                    success=True,
                    cv=cv,
                )
            )
            succeeded += 1

        except ValueError as exc:
            results.append(
                CVUploadResult(
                    filename=file.filename or "unknown",
                    success=False,
                    error=str(exc),
                )
            )
            failed += 1
        except Exception as exc:
            results.append(
                CVUploadResult(
                    filename=file.filename or "unknown",
                    success=False,
                    error="An unexpected error occurred during processing.",
                )
            )
            failed += 1

    return CVBatchUploadResponse(
        results=results,
        summary={"succeeded": succeeded, "failed": failed},
    )


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
