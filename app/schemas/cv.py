from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from typing import TypeAlias

from app.core.pagination import PaginatedResponse, PaginationParams


class CvAnalysisResponse(BaseModel):
    fit_summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    likely_fit_level: str = ""
    resume_improvements: list[str] = Field(default_factory=list)
    ats_improvements: list[str] = Field(default_factory=list)
    recruiter_improvements: list[str] = Field(default_factory=list)
    rewritten_bullets: list[str] = Field(default_factory=list)
    interview_focus: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class CVRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    display_name: str
    summary: str
    library_summary: str
    has_file: bool = False
    is_favorite: bool = False
    tags: list[str]
    created_at: datetime


class CVDownloadResponse(BaseModel):
    url: str


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


class CVBulkDeleteRequest(BaseModel):
    cv_ids: list[int] = Field(default_factory=list)


class CVBulkTagRequest(BaseModel):
    cv_ids: list[int] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class BulkActionResponse(BaseModel):
    updated: int = 0
    deleted: int = 0
    failed: int = 0


CVListResponse: TypeAlias = PaginatedResponse[CVRead]
