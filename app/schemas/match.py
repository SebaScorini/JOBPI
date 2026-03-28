from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.cv import CvAnalysisResponse

MatchLevel = Literal["strong", "medium", "weak"]


class CVMatchRequest(BaseModel):
    cv_id: int


class CVJobMatchRead(BaseModel):
    id: int
    user_id: int
    cv_id: int
    job_id: int
    fit_level: str
    fit_summary: str
    why_this_cv: str
    strengths: list[str]
    missing_skills: list[str]
    improvement_suggestions: list[str]
    match_level: MatchLevel
    recommended: bool
    created_at: datetime


class CVJobMatchDetailRead(CVJobMatchRead):
    heuristic_score: float
    result: CvAnalysisResponse
