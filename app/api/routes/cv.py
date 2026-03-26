import logging
import time

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.schemas.cv import CvAnalysisResponse
from app.services.cv_analyzer import get_cv_analyzer_service
from app.services.job_preprocessing import clean_description
from app.services.pdf_extractor import extract_cv_text

router = APIRouter(tags=["cv"])
logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/cv/analyze", response_model=CvAnalysisResponse)
@router.post("/analyze-fit", response_model=CvAnalysisResponse)
async def analyze_fit(
    title: str = Form(..., min_length=1, max_length=200),
    description: str = Form(..., min_length=50, max_length=20000),
    cv: UploadFile = File(...),
) -> CvAnalysisResponse:
    request_start = time.perf_counter()

    # Validate content type
    if cv.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file must be a PDF.",
        )

    file_bytes = await cv.read()

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="PDF file must be under 5 MB.",
        )

    try:
        cv_text = extract_cv_text(file_bytes)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    job_preprocess_start = time.perf_counter()
    cleaned_job = clean_description(description)
    logger.info(
        "cv_fit job_preprocess_ms=%.1f",
        (time.perf_counter() - job_preprocess_start) * 1000,
    )

    service = get_cv_analyzer_service()
    try:
        return service.analyze(
            job_title=title,
            job_description=cleaned_job,
            cv_text=cv_text,
        )
    finally:
        logger.info(
            "cv_fit total_request_ms=%.1f",
            (time.perf_counter() - request_start) * 1000,
        )
