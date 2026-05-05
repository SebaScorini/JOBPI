from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.schemas.job import AIResponseLanguage


class LinkedInProfileRequest(BaseModel):
    cv_id: int = Field(..., gt=0)
    job_ids: list[int] = Field(default_factory=list, max_length=5)
    language: AIResponseLanguage = "english"
    regenerate: bool = False

    @field_validator("job_ids", mode="before")
    @classmethod
    def default_job_ids(cls, value: object) -> object:
        return [] if value is None else value


class LinkedInProfileRead(BaseModel):
    headline: str
    about_summary: str
    keywords: list[str] = Field(default_factory=list)
    optimization_tips: list[str] = Field(default_factory=list)


class ColdOutreachRequest(BaseModel):
    job_id: int = Field(..., gt=0)
    cv_id: int = Field(..., gt=0)
    hiring_manager_name: str | None = Field(default=None, max_length=120)
    language: AIResponseLanguage = "english"
    regenerate: bool = False

    @field_validator("hiring_manager_name", mode="before")
    @classmethod
    def normalize_hiring_manager_name(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = " ".join(value.split()).strip()
            return stripped or None
        return value


class ColdOutreachRead(BaseModel):
    connection_message: str = Field(..., max_length=300)
    personalization_notes: list[str] = Field(default_factory=list)


