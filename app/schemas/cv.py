from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    library_summary: str
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
    summary: dict[str, int] = Field(default_factory=dict)


class CVTagsUpdate(BaseModel):
    tags: list[str]


class PaginationParams(BaseModel):
    """Query parameters for list endpoints with pagination."""
    limit: int = Field(default=20, ge=1, le=200)
    offset: int = Field(default=0)  # No ge=0 constraint; validator will clamp
    
    @field_validator('offset', mode='before')
    @classmethod
    def validate_offset(cls, v) -> int:
        """Clamp negative offsets to 0."""
        try:
            offset = int(v)
            return max(0, offset)
        except (ValueError, TypeError):
            return 0


class CVListResponse(BaseModel):
    """Paginated CV list response."""
    items: list[CVRead]
    total: int
    limit: int
    offset: int
    has_more: bool = Field(default=False)
