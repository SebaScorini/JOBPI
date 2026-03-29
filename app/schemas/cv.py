from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CvAnalysisResponse(BaseModel):
    fit_summary: str
    strengths: list[str]
    missing_skills: list[str]
    likely_fit_level: str
    resume_improvements: list[str]
    interview_focus: list[str]
    next_steps: list[str]


class CVRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    display_name: str
    summary: str
    tags: list[str]
    created_at: datetime


class CVDetailRead(CVRead):
    raw_text: str
    clean_text: str


class CVUploadResult(BaseModel):
    """Result for a single file in batch upload."""
    filename: str
    success: bool
    cv: CVRead | None = None
    error: str | None = None


class CVBatchUploadResponse(BaseModel):
    """Response for batch CV upload."""
    results: list[CVUploadResult]
    summary: dict[str, int] = {}  # {"succeeded": 2, "failed": 1}


class CVTagsUpdate(BaseModel):
    tags: list[str]
