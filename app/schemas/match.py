from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.cv import CvAnalysisResponse
from app.schemas.job import AIResponseLanguage

MatchLevel = Literal["strong", "medium", "weak"]


class CVMatchRequest(BaseModel):
    cv_id: int
    language: AIResponseLanguage = "english"


class CVCompareRequest(BaseModel):
    cv_id_a: int
    cv_id_b: int
    language: AIResponseLanguage = "english"


class CVComparisonBetterCV(BaseModel):
    cv_id: int
    label: str


class CVComparisonResponse(BaseModel):
    better_cv: CVComparisonBetterCV
    explanation: str
    strengths_a: list[str]
    strengths_b: list[str]


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
    suggested_improvements: list[str]
    missing_keywords: list[str]
    reorder_suggestions: list[str] | None = None
    match_level: MatchLevel
    recommended: bool
    created_at: datetime


class CVJobMatchDetailRead(CVJobMatchRead):
    heuristic_score: float
    result: CvAnalysisResponse
