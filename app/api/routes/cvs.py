from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlmodel import Session

from app.core.config import get_settings
from app.core.rate_limit import RateLimitPolicy, enforce_rate_limit
from app.core.validation import reject_oversized_request
from app.db.database import get_session
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas.cv import CVDetailRead, CVRead, CVBatchUploadResponse, CVTagsUpdate, CVUploadResult
from app.services.cv_library_service import get_cv_library_service


router = APIRouter(prefix="/cvs", tags=["cvs"])


@router.post("/upload", response_model=CVRead, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    request: Request,
    display_name: str = Form(..., min_length=1, max_length=200),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CVRead:
    settings = get_settings()
    is_trusted_user = settings.should_bypass_user_limits(current_user.email)
    if not is_trusted_user:
        reject_oversized_request(
            request=request,
            max_bytes=settings.max_pdf_size_bytes + 256 * 1024,
            detail=f"Request body is too large. PDF file must be under {settings.max_pdf_size_mb} MB.",
        )
    enforce_rate_limit(
        request=request,
        user=current_user,
        policy=RateLimitPolicy(
            name="cv_upload",
            limit=settings.cv_upload_limit,
            window_seconds=settings.cv_upload_window_seconds,
        ),
    )

    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file must be a PDF.",
        )

    file_bytes = await file.read()
    if not is_trusted_user and len(file_bytes) > settings.max_pdf_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"PDF file must be under {settings.max_pdf_size_mb} MB.",
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
    request: Request,
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

    settings = get_settings()
    is_trusted_user = settings.should_bypass_user_limits(current_user.email)
    if not is_trusted_user:
        reject_oversized_request(
            request=request,
            max_bytes=(settings.max_pdf_size_bytes * settings.max_cvs_per_upload) + 512 * 1024,
            detail=(
                "Request body is too large. "
                f"Upload up to {settings.max_cvs_per_upload} PDF files under {settings.max_pdf_size_mb} MB each."
            ),
        )
    if not is_trusted_user and len(files) > settings.max_cvs_per_upload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"You can upload up to {settings.max_cvs_per_upload} CVs per request.",
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
            if not is_trusted_user and len(file_bytes) > settings.max_pdf_size_bytes:
                results.append(
                    CVUploadResult(
                        filename=file.filename or "unknown",
                        success=False,
                        error=f"PDF file must be under {settings.max_pdf_size_mb} MB.",
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


@router.get("", response_model=dict)
def list_cvs(
    limit: int = 20,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List user's CVs with pagination. Default returns 20 most recent CVs.
    
    Query params:
        - limit: Number of items (1-200, default 20)
        - offset: Pagination offset (default 0)
    """
    from app.schemas.cv import CVListResponse
    
    # Clamp and validate
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    
    cvs, total = get_cv_library_service().list_cvs(session, current_user, limit=limit, offset=offset)
    return CVListResponse(
        items=cvs,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    ).model_dump()


@router.get("/{cv_id}", response_model=CVDetailRead)
def get_cv(
    cv_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CVDetailRead:
    return get_cv_library_service().get_cv(session, current_user, cv_id)


@router.patch("/{cv_id}/tags", response_model=CVRead)
def update_cv_tags(
    cv_id: int,
    payload: CVTagsUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> CVRead:
    return get_cv_library_service().update_cv_tags(session, current_user, cv_id, payload.tags)


@router.delete("/{cv_id}")
def delete_cv(
    cv_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    get_cv_library_service().delete_cv(session, current_user, cv_id)
    return {"ok": True}
