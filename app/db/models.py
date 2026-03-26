from datetime import datetime, timezone

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StoredCV(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=200)
    file_hash: str = Field(index=True, unique=True, max_length=64)
    cleaned_text: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class JobAnalysis(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    job_hash: str = Field(index=True, unique=True, max_length=64)
    title: str = Field(max_length=200)
    company: str = Field(max_length=200)
    cleaned_description: str = Field(sa_column=Column(Text, nullable=False))
    result_json: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class CVJobMatch(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("cv_id", "job_id"),)

    id: int | None = Field(default=None, primary_key=True)
    cv_id: int = Field(foreign_key="storedcv.id", index=True)
    job_id: int = Field(foreign_key="jobanalysis.id", index=True)
    result_json: str = Field(sa_column=Column(Text, nullable=False))
    heuristic_score: float = Field(nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
