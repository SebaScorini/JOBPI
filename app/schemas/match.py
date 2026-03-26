from datetime import datetime

from pydantic import BaseModel

from app.schemas.cv import CvAnalysisResponse


class CVMatchRequest(BaseModel):
    cv_id: int


class CVJobMatchRead(BaseModel):
    id: int
    user_id: int
    cv_id: int
    job_id: int
    fit_level: str
    fit_summary: str
    strengths: list[str]
    missing_skills: list[str]
    recommended: bool
    created_at: datetime


class CVJobMatchDetailRead(CVJobMatchRead):
    heuristic_score: float
    result: CvAnalysisResponse
