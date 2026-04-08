from datetime import datetime
from typing import Literal
from typing import TypeAlias

from pydantic import BaseModel, Field

from app.core.pagination import PaginatedResponse
from app.schemas.cv import CvAnalysisResponse
from app.schemas.job import AIResponseLanguage

MatchLevel = Literal["strong", "medium", "weak"]


class CVMatchRequest(BaseModel):
    cv_id: int = Field(..., gt=0)
    language: AIResponseLanguage = "english"
    regenerate: bool = False


class CVCompareRequest(BaseModel):
    cv_id_a: int = Field(..., gt=0)
    cv_id_b: int = Field(..., gt=0)
    language: AIResponseLanguage = "english"


class CVComparisonWinner(BaseModel):
    cv_id: int
    label: str


class CVComparisonResponse(BaseModel):
    winner: CVComparisonWinner
    overall_reason: str
    comparative_strengths: list[str]
    comparative_weaknesses: list[str]
    job_alignment_breakdown: list[str]


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


MatchListResponse: TypeAlias = PaginatedResponse[CVJobMatchRead]
