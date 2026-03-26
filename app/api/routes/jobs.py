from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.database import get_session
from app.schemas.job import JobAnalysisRequest, JobAnalysisResponse
from app.services.job_analyzer import get_job_analyzer_service


router = APIRouter(tags=["jobs"])


@router.post("/jobs/analyze", response_model=JobAnalysisResponse)
@router.post("/analyze-job", response_model=JobAnalysisResponse)
def analyze_job(
    payload: JobAnalysisRequest,
    session: Session = Depends(get_session),
) -> JobAnalysisResponse:
    service = get_job_analyzer_service()
    return service.analyze(payload, session=session)
