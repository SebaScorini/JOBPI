from datetime import datetime
from typing import Literal
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from app.core.pagination import PaginatedResponse


AIResponseLanguage = Literal["english", "spanish"]


class JobAnalysisRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    company: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=50, max_length=20000)
    language: AIResponseLanguage = "english"
    regenerate: bool = False


class JobAnalysisPayload(BaseModel):
    summary: str
    seniority: str
    role_type: str
    required_skills: list[str]
    nice_to_have_skills: list[str]
    responsibilities: list[str]
    how_to_prepare: list[str]
    learning_path: list[str]
    missing_skills: list[str]
    resume_tips: list[str]
    interview_tips: list[str]
    portfolio_project_ideas: list[str]


class JobAnalysisResponse(JobAnalysisPayload):
    job_id: int | None = None


JobStatus = Literal["saved", "applied", "interview", "rejected", "offer"]


class JobStatusUpdateRequest(BaseModel):
    status: JobStatus
    applied_date: datetime | None = None


class JobNotesUpdateRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class CoverLetterGenerateRequest(BaseModel):
    selected_cv_id: int = Field(..., gt=0)
    language: AIResponseLanguage = "english"
    regenerate: bool = False


class CoverLetterGenerateResponse(BaseModel):
    generated_cover_letter: str


class JobDeleteResponse(BaseModel):
    success: bool = True


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    description: str
    clean_description: str
    analysis_result: JobAnalysisPayload
    is_saved: bool = False
    status: JobStatus = "saved"
    applied_date: datetime | None = None
    notes: str | None = None
    created_at: datetime | None


JobListResponse: TypeAlias = PaginatedResponse[JobRead]
