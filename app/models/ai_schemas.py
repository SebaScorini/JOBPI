from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Generic, TypeVar

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


StrictModelConfig = ConfigDict(extra="forbid", strict=True)


class AIValidationIssue(BaseModel):
    model_config = StrictModelConfig

    field_path: str
    message: str
    input_value: str | None = None


T = TypeVar("T", bound=BaseModel)


@dataclass(slots=True)
class AIParsedResult(Generic[T]):
    payload: T
    raw_output: object
    schema_name: str


@dataclass(slots=True)
class AIOutputValidationFailure(Exception):
    operation: str
    schema_name: str
    failure_category: str
    raw_output: object
    issues: list[AIValidationIssue] = field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.operation} failed validation for {self.schema_name} ({self.failure_category})"


def _normalize_string_list(value: object, *, limit: int) -> list[str]:
    if value is None:
        return []

    def _flatten(item: object) -> list[str]:
        if item is None:
            return []
        if isinstance(item, str):
            text = item.strip()
            if not text:
                return []
            if "\n" in text:
                return [part.strip(" -•\t") for part in text.splitlines() if part.strip(" -•\t")]
            if "," in text:
                parts = [part.strip(" -•\t") for part in text.split(",") if part.strip(" -•\t")]
                if len(parts) > 1:
                    return parts
            return [text]
        if isinstance(item, (list, tuple, set)):
            flattened: list[str] = []
            for nested in item:
                flattened.extend(_flatten(nested))
            return flattened
        return [str(item).strip()]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in _flatten(value):
        cleaned = " ".join(item.split()).strip(" -•\t")
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
        if len(normalized) >= limit:
            break
    return normalized


def _normalize_short_text(value: object, *, limit: int) -> str:
    if not isinstance(value, str):
        if value is None:
            return ""
        value = str(value)

    text = " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip(" \"'-")
    if not text:
        return ""

    text = re.sub(r"\[\[[^\]]*\]\]", "", text).strip()
    text = re.sub(r"\s*\.\.\.\s*$", "", text).strip()
    if len(text) <= limit:
        return text

    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
    ]
    if sentences:
        selected: list[str] = []
        for sentence in sentences:
            candidate = " ".join(selected + [sentence]).strip()
            if len(candidate) > limit:
                break
            selected.append(sentence)
        if selected:
            return " ".join(selected).rstrip(" ,;:")

    cutoff = max(
        text.rfind(". ", 0, limit),
        text.rfind("; ", 0, limit),
        text.rfind(": ", 0, limit),
        text.rfind(", ", 0, limit),
        text.rfind(" ", 0, limit),
    )
    if cutoff < int(limit * 0.6):
        cutoff = limit
    truncated = text[:cutoff].rstrip(" ,;:")
    truncated = re.sub(
        r"\b(?:and|or|with|using|including|about|for|to|in|on|across|through|experienced in|skilled in)\s*$",
        "",
        truncated,
        flags=re.IGNORECASE,
    ).rstrip(" ,;:")
    return truncated


def _normalize_ai_text(value: object) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        value = str(value)

    text = " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip(" \"'-")
    text = re.sub(r"\[\[[^\]]*\]\]", "", text).strip()
    text = re.sub(r"\s*\.\.\.\s*$", "", text).strip()
    return text


def _normalize_enum_like_text(value: object, *, mapping: dict[str, tuple[str, ...]]) -> str:
    text = _normalize_ai_text(value)
    lowered = text.lower()
    for canonical, patterns in mapping.items():
        if any(pattern in lowered for pattern in patterns):
            return canonical
    return text


class JobAnalysisAIOutput(BaseModel):
    model_config = StrictModelConfig

    summary: str = Field(min_length=1, max_length=500)
    seniority: str = Field(min_length=1, max_length=40)
    role_type: str = Field(min_length=1, max_length=40)
    req_skills: list[str] = Field(
        default_factory=list,
        max_length=5,
        validation_alias=AliasChoices("req_skills", "required_skills"),
    )
    nice_skills: list[str] = Field(
        default_factory=list,
        max_length=5,
        validation_alias=AliasChoices("nice_skills", "nice_to_have_skills"),
    )
    responsibilities: list[str] = Field(default_factory=list, max_length=5)
    prep: list[str] = Field(
        default_factory=list,
        max_length=4,
        validation_alias=AliasChoices("prep", "how_to_prepare"),
    )
    learn: list[str] = Field(
        default_factory=list,
        max_length=4,
        validation_alias=AliasChoices("learn", "learning_path"),
    )
    gaps: list[str] = Field(
        default_factory=list,
        max_length=5,
        validation_alias=AliasChoices("gaps", "missing_skills"),
    )
    resume: list[str] = Field(
        default_factory=list,
        max_length=4,
        validation_alias=AliasChoices("resume", "resume_tips"),
    )
    interview: list[str] = Field(
        default_factory=list,
        max_length=4,
        validation_alias=AliasChoices("interview", "interview_tips"),
    )
    projects: list[str] = Field(
        default_factory=list,
        max_length=3,
        validation_alias=AliasChoices("projects", "portfolio_project_ideas"),
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_lists(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "summary" in normalized:
            normalized["summary"] = _normalize_short_text(normalized["summary"], limit=500)
        if "seniority" in normalized:
            normalized["seniority"] = _normalize_enum_like_text(
                normalized["seniority"],
                mapping={
                    "junior": ("junior", "jr", "entry level", "entry-level", "trainee", "intern"),
                    "mid": ("mid", "mid-level", "mid level", "semi-senior", "semi senior", "ssr"),
                    "senior": ("senior", "sr", "principal", "staff", "expert"),
                    "lead": ("lead", "team lead", "tech lead", "engineering lead", "head of"),
                    "unknown": ("unknown", "not specified", "not clear", "unclear", "n/a"),
                },
            )
        if "role_type" in normalized:
            normalized["role_type"] = _normalize_enum_like_text(
                normalized["role_type"],
                mapping={
                    "backend": ("backend", "back-end", "api", "services"),
                    "full-stack": ("full stack", "full-stack", "front-end and back-end", "frontend and backend"),
                    "frontend": ("frontend", "front-end", "ui", "ux"),
                    "data": ("data", "analytics", "machine learning", "ml", "etl", "bi"),
                    "devops": ("devops", "sre", "platform", "infrastructure", "terraform"),
                    "mobile": ("mobile", "ios", "android", "flutter", "react native"),
                    "qa": ("qa", "quality assurance", "test automation", "testing"),
                    "product": ("product", "product manager", "product management", "pm"),
                    "generalist": ("generalist", "cross-functional", "cross functional"),
                },
            )
        list_limits = {
            "req_skills": 5,
            "required_skills": 5,
            "nice_skills": 5,
            "nice_to_have_skills": 5,
            "responsibilities": 5,
            "prep": 4,
            "how_to_prepare": 4,
            "learn": 4,
            "learning_path": 4,
            "gaps": 5,
            "missing_skills": 5,
            "resume": 4,
            "resume_tips": 4,
            "interview": 4,
            "interview_tips": 4,
            "projects": 3,
            "portfolio_project_ideas": 3,
        }
        for key, limit in list_limits.items():
            if key in normalized:
                normalized[key] = _normalize_string_list(normalized[key], limit=limit)
        return normalized


class CvAnalysisAIOutput(BaseModel):
    model_config = StrictModelConfig

    fit_summary: str = Field(min_length=1, max_length=1200)
    strengths: list[str] = Field(default_factory=list, max_length=5)
    missing_skills: list[str] = Field(default_factory=list, max_length=5)
    likely_fit_level: str = Field(
        min_length=1,
        max_length=40,
        validation_alias=AliasChoices("likely_fit_level", "fit_level", "match_level"),
    )
    resume_improvements: list[str] = Field(default_factory=list, max_length=4)
    ats_improvements: list[str] = Field(default_factory=list, max_length=4)
    recruiter_improvements: list[str] = Field(default_factory=list, max_length=4)
    rewritten_bullets: list[str] = Field(default_factory=list, max_length=4)
    interview_focus: list[str] = Field(default_factory=list, max_length=4)
    next_steps: list[str] = Field(default_factory=list, max_length=4)

    @model_validator(mode="before")
    @classmethod
    def normalize_lists(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "fit_summary" in normalized:
            normalized["fit_summary"] = _normalize_short_text(normalized["fit_summary"], limit=1200)
        fit_level_key = None
        fit_level_value = None
        for key in ("likely_fit_level", "fit_level", "match_level"):
            if key in normalized:
                fit_level_key = key
                fit_level_value = normalized[key]
                break
        if fit_level_value is not None:
            normalized["likely_fit_level"] = _normalize_enum_like_text(
                fit_level_value,
                mapping={
                    "Strong": ("strong", "very strong", "high fit", "excellent", "great fit", "good fit"),
                    "Moderate": ("moderate", "medium", "mid", "partial fit", "average", "decent", "fair"),
                    "Weak": ("weak", "low fit", "poor fit", "not a fit", "mismatch", "poor", "low"),
                },
            )
            if fit_level_key in {"fit_level", "match_level"}:
                normalized.pop(fit_level_key, None)
        list_limits = {
            "strengths": 5,
            "missing_skills": 5,
            "resume_improvements": 4,
            "ats_improvements": 4,
            "recruiter_improvements": 4,
            "rewritten_bullets": 4,
            "interview_focus": 4,
            "next_steps": 4,
        }
        for key, limit in list_limits.items():
            if key in normalized:
                normalized[key] = _normalize_string_list(normalized[key], limit=limit)
        return normalized


class CoverLetterAIOutput(BaseModel):
    model_config = StrictModelConfig

    cover_letter: str = Field(min_length=1, max_length=3000)


class CvLibrarySummaryAIOutput(BaseModel):
    model_config = StrictModelConfig

    summary: str = Field(min_length=1, max_length=300)

    @model_validator(mode="before")
    @classmethod
    def normalize_summary(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "summary" in normalized:
            normalized["summary"] = _normalize_short_text(normalized["summary"], limit=300)
        return normalized


class InterviewQuestionItem(BaseModel):
    model_config = StrictModelConfig

    question: str = Field(min_length=1, max_length=500)
    category: str = Field(min_length=1, max_length=40)
    difficulty: str = Field(min_length=1, max_length=20)
    rationale: str = Field(min_length=1, max_length=500)

    @model_validator(mode="before")
    @classmethod
    def normalize_question(cls, value: object) -> object:
        if isinstance(value, str):
            parsed = _parse_interview_question_string(value)
            if parsed is not None:
                return parsed
            return {
                "question": _normalize_short_text(value, limit=500),
                "category": "behavioral",
                "difficulty": "medium",
                "rationale": "Assessed from the job and CV context.",
            }
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        if "question" in normalized:
            normalized["question"] = _normalize_short_text(normalized["question"], limit=500)
        if "category" in normalized:
            normalized["category"] = _normalize_interview_category(normalized["category"])
        if "difficulty" in normalized:
            normalized["difficulty"] = _normalize_interview_difficulty(normalized["difficulty"])
        if "rationale" in normalized:
            normalized["rationale"] = _normalize_short_text(normalized["rationale"], limit=500)
        return normalized


class InterviewQuestionsAIOutput(BaseModel):
    model_config = StrictModelConfig

    questions: list[InterviewQuestionItem] = Field(default_factory=list, min_length=5, max_length=7)
    focus_areas: list[str] = Field(default_factory=list, min_length=2, max_length=5)

    @model_validator(mode="before")
    @classmethod
    def normalize_questions(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "questions" in normalized:
            normalized["questions"] = _normalize_interview_question_items(normalized["questions"])
        if "focus_areas" in normalized:
            normalized["focus_areas"] = _normalize_string_list(normalized["focus_areas"], limit=5)
        return normalized


class InterviewEvaluationAIOutput(BaseModel):
    model_config = StrictModelConfig

    score: int = Field(ge=1, le=10)
    feedback: str = Field(min_length=1, max_length=1200)
    ideal_answer: str = Field(min_length=1, max_length=1500)
    improvement_tips: list[str] = Field(default_factory=list, min_length=2, max_length=3)

    @model_validator(mode="before")
    @classmethod
    def normalize_evaluation(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "score" in normalized:
            normalized["score"] = _normalize_interview_score(normalized["score"])
        if "feedback" in normalized:
            normalized["feedback"] = _normalize_short_text(normalized["feedback"], limit=1200)
        if "ideal_answer" in normalized:
            normalized["ideal_answer"] = _normalize_short_text(normalized["ideal_answer"], limit=1500)
        if "improvement_tips" in normalized:
            normalized["improvement_tips"] = _normalize_string_list(normalized["improvement_tips"], limit=3)
        return normalized


def _normalize_interview_question_items(value: object) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()

    if isinstance(value, str):
        value = [value]

    if not isinstance(value, list):
        return items

    for item in value:
        parsed = _coerce_interview_question_item(item)
        if parsed is None:
            continue
        normalized_question = parsed.get("question", "")
        if not normalized_question:
            continue
        key = normalized_question.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        items.append(parsed)
        if len(items) >= 7:
            break
    return items


def _coerce_interview_question_item(item: object) -> dict[str, str] | None:
    if isinstance(item, InterviewQuestionItem):
        return item.model_dump()
    if isinstance(item, dict):
        return {
            "question": _normalize_short_text(item.get("question", ""), limit=500),
            "category": _normalize_interview_category(item.get("category", "behavioral")),
            "difficulty": _normalize_interview_difficulty(item.get("difficulty", "medium")),
            "rationale": _normalize_short_text(item.get("rationale", ""), limit=500),
        }
    if not isinstance(item, str):
        return None

    parsed = _parse_interview_question_string(item)
    if parsed is not None:
        return parsed
    return {
        "question": _normalize_short_text(item, limit=500),
        "category": "behavioral",
        "difficulty": "medium",
        "rationale": "Assessed from the job and CV context.",
    }


def _parse_interview_question_string(value: str) -> dict[str, str] | None:
    text = value.strip()
    if not text:
        return None
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return _coerce_interview_question_item(parsed)
    if "|" in text:
        parts = [part.strip() for part in text.split("|")]
        if len(parts) >= 4:
            return {
                "question": _normalize_short_text(parts[0], limit=500),
                "category": _normalize_interview_category(parts[1]),
                "difficulty": _normalize_interview_difficulty(parts[2]),
                "rationale": _normalize_short_text(" | ".join(parts[3:]), limit=500),
            }
    return None


def _normalize_interview_category(value: object) -> str:
    text = _normalize_ai_text(value)
    lowered = text.lower()
    if any(token in lowered for token in ("technical", "system design", "coding", "debug", "architecture")):
        return "technical"
    if any(token in lowered for token in ("situational", "scenario", "case", "problem solving")):
        return "situational"
    if any(token in lowered for token in ("culture", "fit", "values", "team", "collaboration")):
        return "culture_fit"
    if lowered in {"behavioral", "behavioural"} or not lowered:
        return "behavioral"
    return "behavioral"


def _normalize_interview_difficulty(value: object) -> str:
    text = _normalize_ai_text(value)
    lowered = text.lower()
    if any(token in lowered for token in ("hard", "senior", "advanced")):
        return "hard"
    if any(token in lowered for token in ("easy", "basic", "simple", "junior")):
        return "easy"
    if lowered == "medium" or not lowered:
        return "medium"
    return "medium"


def _normalize_interview_score(value: object) -> int:
    try:
        if value is None:
            return 1
        if isinstance(value, (int, float)):
            numeric = float(value)
        elif isinstance(value, str):
            numeric = float(value)
        else:
            return 1
        score = int(numeric)
    except (TypeError, ValueError):
        return 1
    return max(1, min(10, score))
