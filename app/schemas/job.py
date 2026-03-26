from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobAnalysisRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    company: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=50, max_length=20000)


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


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    description: str
    clean_description: str
    analysis_result: JobAnalysisPayload
    created_at: datetime | None
