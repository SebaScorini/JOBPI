from fastapi import APIRouter

from app.schemas.job import JobAnalysisRequest, JobAnalysisResponse
from app.services.job_analyzer import get_job_analyzer_service


router = APIRouter(tags=["jobs"])


@router.post("/analyze-job", response_model=JobAnalysisResponse)
def analyze_job(payload: JobAnalysisRequest) -> JobAnalysisResponse:
    service = get_job_analyzer_service()
    return service.analyze(payload)
