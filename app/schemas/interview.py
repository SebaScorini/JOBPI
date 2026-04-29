from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.job import AIResponseLanguage


InterviewSessionType = Literal["mixed", "behavioral", "technical"]
InterviewSessionStatus = Literal["in_progress", "completed"]


class InterviewSessionCreate(BaseModel):
    cv_id: int = Field(..., gt=0)
    session_type: InterviewSessionType = "mixed"
    language: AIResponseLanguage = "english"


class InterviewAnswerSubmit(BaseModel):
    question_index: int = Field(..., ge=0)
    answer_text: str = Field(..., min_length=1, max_length=8000)

    @field_validator("answer_text", mode="before")
    @classmethod
    def strip_and_reject_blank(cls, v: object) -> object:
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("answer_text must not be empty or whitespace-only")
            return stripped
        return v


class InterviewQuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index: int
    question: str
    category: str
    difficulty: str
    rationale: str


class InterviewAnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_index: int
    answer_text: str
    answered_at: datetime


class InterviewEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_index: int
    score: int
    feedback: str
    ideal_answer: str
    improvement_tips: list[str] = Field(default_factory=list)
    evaluated_at: datetime


class InterviewSessionSummaryRead(BaseModel):
    focus_areas: list[str] = Field(default_factory=list)
    overall_score: float | None = None
    strong_areas: list[str] = Field(default_factory=list)
    weak_areas: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class InterviewSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    job_id: int
    cv_id: int
    session_type: InterviewSessionType
    language: AIResponseLanguage
    status: InterviewSessionStatus
    questions: list[InterviewQuestionRead] = Field(default_factory=list)
    answers: list[InterviewAnswerRead] = Field(default_factory=list)
    evaluations: list[InterviewEvaluationRead] = Field(default_factory=list)
    summary: InterviewSessionSummaryRead | None = None
    current_question_index: int = 0
    next_question_index: int | None = None
    is_complete: bool = False
    created_at: datetime
    updated_at: datetime | None = None


class InterviewFeedbackRead(InterviewEvaluationRead):
    session_id: int
    answer_text: str = ""
    is_complete: bool = False
    next_question_index: int | None = None
    summary: InterviewSessionSummaryRead | None = None