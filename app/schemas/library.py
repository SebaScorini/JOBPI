from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.cv import CvAnalysisResponse


class StoredCVRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class CVJobMatchRead(BaseModel):
    id: int
    cv_id: int
    job_id: int
    heuristic_score: float
    result: CvAnalysisResponse
    created_at: datetime


class RecommendationMatchRead(BaseModel):
    cv_id: int
    score: float


class RecommendationCVRead(BaseModel):
    id: int
    name: str


class RecommendationRead(BaseModel):
    best_cv: RecommendationCVRead
    score: float
    matches: list[RecommendationMatchRead]


class CVJobMatchRequest(BaseModel):
    cv_id: int
    job_id: int
