from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel import Session

from app.db.database import get_session
from app.schemas.library import CVJobMatchRead, CVJobMatchRequest, RecommendationRead, StoredCVRead
from app.services.cv_library_service import get_cv_library_service


router = APIRouter(prefix="/library", tags=["library"])

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/cvs", response_model=StoredCVRead, status_code=status.HTTP_201_CREATED)
async def upload_cv(
    name: str = Form(..., min_length=1, max_length=200),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> StoredCVRead:
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
        return service.upload_cv(session, name=name, file_bytes=file_bytes)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/cvs", response_model=list[StoredCVRead])
def list_cvs(session: Session = Depends(get_session)) -> list[StoredCVRead]:
    service = get_cv_library_service()
    return service.list_cvs(session)


@router.get("/cvs/{cv_id}", response_model=StoredCVRead)
def get_cv(cv_id: int, session: Session = Depends(get_session)) -> StoredCVRead:
    service = get_cv_library_service()
    return service.get_cv(session, cv_id)


@router.delete("/cvs/{cv_id}")
def delete_cv(cv_id: int, session: Session = Depends(get_session)) -> dict[str, bool]:
    service = get_cv_library_service()
    service.delete_cv(session, cv_id)
    return {"ok": True}


@router.post("/match", response_model=CVJobMatchRead)
def match_cv(payload: CVJobMatchRequest, session: Session = Depends(get_session)) -> CVJobMatchRead:
    service = get_cv_library_service()
    return service.match_cv_to_job(session, cv_id=payload.cv_id, job_id=payload.job_id)


@router.get("/recommend/{job_id}", response_model=RecommendationRead)
def recommend_best_cv(job_id: int, session: Session = Depends(get_session)) -> RecommendationRead:
    service = get_cv_library_service()
    return service.recommend_best_cv(session, job_id)
