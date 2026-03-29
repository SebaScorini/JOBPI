from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import JSON, Column, String, Text, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(sa_column=Column(String(255), unique=True, index=True, nullable=False))
    hashed_password: str = Field(sa_column=Column(String(255), nullable=False))
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)

    cvs: List["CV"] = Relationship(back_populates="user")
    jobs: List["JobAnalysis"] = Relationship(back_populates="user")
    matches: List["CVJobMatch"] = Relationship(back_populates="user")


class CV(SQLModel, table=True):
    __tablename__ = "cvs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    filename: str = Field(sa_column=Column(String(255), nullable=False))
    display_name: str = Field(sa_column=Column(String(255), nullable=False))
    raw_text: str = Field(sa_column=Column(Text, nullable=False))
    clean_text: str = Field(sa_column=Column(Text, nullable=False))
    summary: str = Field(sa_column=Column(Text, nullable=False))
    library_summary: str = Field(sa_column=Column(Text, nullable=False, default=""))
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False, default=list))
    created_at: datetime = Field(default_factory=utc_now, nullable=False)

    user: Optional[User] = Relationship(back_populates="cvs")
    matches: List["CVJobMatch"] = Relationship(back_populates="cv")


class JobAnalysis(SQLModel, table=True):
    __tablename__ = "job_analyses"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    title: str = Field(sa_column=Column(String(255), nullable=False))
    company: str = Field(sa_column=Column(String(255), nullable=False))
    description: str = Field(sa_column=Column(Text, nullable=False))
    clean_description: str = Field(sa_column=Column(Text, nullable=False))
    analysis_result: dict = Field(sa_column=Column(JSON, nullable=False))
    status: str = Field(sa_column=Column(String(20), nullable=False, default="saved"), default="saved")
    applied_date: Optional[datetime] = Field(default=None, nullable=True)
    notes: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(default_factory=utc_now, nullable=False)

    user: Optional[User] = Relationship(back_populates="jobs")
    matches: List["CVJobMatch"] = Relationship(back_populates="job")


class CVJobMatch(SQLModel, table=True):
    __tablename__ = "cv_job_matches"
    __table_args__ = (UniqueConstraint("user_id", "cv_id", "job_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    cv_id: int = Field(foreign_key="cvs.id", index=True, nullable=False)
    job_id: int = Field(foreign_key="job_analyses.id", index=True, nullable=False)
    fit_level: str = Field(sa_column=Column(String(50), nullable=False))
    fit_summary: str = Field(sa_column=Column(Text, nullable=False))
    strengths: list[str] = Field(sa_column=Column(JSON, nullable=False))
    missing_skills: list[str] = Field(sa_column=Column(JSON, nullable=False))
    recommended: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)

    user: Optional[User] = Relationship(back_populates="matches")
    cv: Optional[CV] = Relationship(back_populates="matches")
    job: Optional[JobAnalysis] = Relationship(back_populates="matches")
