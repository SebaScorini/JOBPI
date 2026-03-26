import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

import dspy
from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.config import configure_dspy, get_settings
from app.db import crud
from app.schemas.job import JobAnalysisRequest, JobAnalysisResponse
from app.services.job_preprocessing import clean_description


MAX_LIST_ITEMS = 5
MAX_ITEM_CHARS = 80
MAX_SUMMARY_CHARS = 240


class LeanJobAnalysisSignature(dspy.Signature):
    """Return short structured job insights."""

    title: str = dspy.InputField(desc="Job title")
    company: str = dspy.InputField(desc="Company name")
    desc: str = dspy.InputField(desc="Cleaned job text")
    summary: str = dspy.OutputField(desc="1-2 short sentences")
    seniority: str = dspy.OutputField(desc="One label")
    role_type: str = dspy.OutputField(desc="One role family")
    req_skills: list[str] = dspy.OutputField(desc="Up to 5 must-have skills")
    nice_skills: list[str] = dspy.OutputField(desc="Up to 5 preferred skills")
    responsibilities: list[str] = dspy.OutputField(desc="Up to 5 core tasks")
    prep: list[str] = dspy.OutputField(desc="Up to 5 prep actions")
    learn: list[str] = dspy.OutputField(desc="Up to 5 learning steps")
    gaps: list[str] = dspy.OutputField(desc="Up to 5 likely missing skills")
    resume: list[str] = dspy.OutputField(desc="Up to 5 resume tips")
    interview: list[str] = dspy.OutputField(desc="Up to 5 interview tips")
    projects: list[str] = dspy.OutputField(desc="Up to 5 project ideas")


class JobAnalyzerModule(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(LeanJobAnalysisSignature)

    def forward(self, title: str, company: str, description: str):
        return self.predict(title=title, company=company, desc=description)


class JobAnalyzerService:
    def __init__(self) -> None:
        configure_dspy()
        settings = get_settings()
        self.analyzer = JobAnalyzerModule()
        self.timeout_seconds = settings.dspy_timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._cache: dict[str, JobAnalysisResponse] = {}

    def analyze(self, payload: JobAnalysisRequest, session: Session | None = None) -> JobAnalysisResponse:
        cleaned_description = clean_description(payload.description)
        cache_key = _build_cache_key(payload.title, payload.company, cleaned_description)

        if session is not None:
            stored = crud.get_job_by_hash(session, cache_key)
            if stored is not None:
                response = JobAnalysisResponse.model_validate_json(stored.result_json)
                response.job_id = stored.id
                self._cache[cache_key] = response.model_copy(deep=True)
                return response

        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached.model_copy(deep=True)

        try:
            future = self._executor.submit(
                self.analyzer,
                title=payload.title,
                company=payload.company,
                description=cleaned_description,
            )
            result = future.result(timeout=self.timeout_seconds)
        except FuturesTimeoutError as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Job analysis timed out. Try a shorter description or retry later.",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to analyze job description: {exc}",
            ) from exc

        response = JobAnalysisResponse(
            summary=_normalize_text(result.summary, MAX_SUMMARY_CHARS),
            seniority=_normalize_text(result.seniority, 40),
            role_type=_normalize_text(result.role_type, 40),
            required_skills=_normalize_list(result.req_skills),
            nice_to_have_skills=_normalize_list(result.nice_skills),
            responsibilities=_normalize_list(result.responsibilities),
            how_to_prepare=_normalize_list(result.prep),
            learning_path=_normalize_list(result.learn),
            missing_skills=_normalize_list(result.gaps),
            resume_tips=_normalize_list(result.resume),
            interview_tips=_normalize_list(result.interview),
            portfolio_project_ideas=_normalize_list(result.projects),
        )
        if session is not None:
            stored = crud.create_job_analysis(
                session,
                job_hash=cache_key,
                title=payload.title,
                company=payload.company,
                cleaned_description=cleaned_description,
                result_json=json.dumps(response.model_dump()),
            )
            response.job_id = stored.id
        self._cache[cache_key] = response.model_copy(deep=True)
        return response


def _normalize_list(value: object) -> list[str]:
    items: list[str] = []

    if isinstance(value, list):
        items = [item for item in value if isinstance(item, str)]

    elif isinstance(value, str):
        normalized = value.replace("\r", "\n")
        parts: list[str] = []
        for line in normalized.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if "," in stripped and not stripped.startswith("-"):
                parts.extend(segment.strip(" -") for segment in stripped.split(",") if segment.strip(" -"))
            else:
                parts.append(stripped.strip(" -"))
        items = parts

    cleaned: list[str] = []
    for item in items:
        short = _normalize_text(item, MAX_ITEM_CHARS)
        if short and short not in cleaned:
            cleaned.append(short)
        if len(cleaned) >= MAX_LIST_ITEMS:
            break
    return cleaned


def _normalize_text(value: object, limit: int) -> str:
    if not isinstance(value, str):
        return ""

    text = " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip(" -")
    if len(text) <= limit:
        return text

    cutoff = text.rfind(" ", 0, limit)
    if cutoff < int(limit * 0.6):
        cutoff = limit
    return text[:cutoff].rstrip(" ,;:.")


def _build_cache_key(title: str, company: str, description: str) -> str:
    payload = f"{title.strip().lower()}|{company.strip().lower()}|{description.strip().lower()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


_service: JobAnalyzerService | None = None


def get_job_analyzer_service() -> JobAnalyzerService:
    global _service
    if _service is None:
        _service = JobAnalyzerService()
    return _service
