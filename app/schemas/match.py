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
    overall_reason: str = ""
    comparative_strengths: list[str] = Field(default_factory=list)
    comparative_weaknesses: list[str] = Field(default_factory=list)
    job_alignment_breakdown: list[str] = Field(default_factory=list)


class CVJobMatchRead(BaseModel):
    id: int
    user_id: int
    cv_id: int
    job_id: int
    fit_level: str = ""
    fit_summary: str = ""
    why_this_cv: str = ""
    strengths: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    suggested_improvements: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    reorder_suggestions: list[str] | None = None
    match_level: MatchLevel = "weak"
    recommended: bool
    created_at: datetime


class CVJobMatchDetailRead(CVJobMatchRead):
    heuristic_score: float = 0.0
    result: CvAnalysisResponse = Field(default_factory=CvAnalysisResponse)


MatchListResponse: TypeAlias = PaginatedResponse[CVJobMatchRead]
