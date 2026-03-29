import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import dspy
from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.ai import build_ai_failure_http_exception, dspy_lm_override, run_ai_call_with_timeout
from app.core.config import configure_dspy, get_settings
from app.db import crud
from app.models import User
from app.schemas.job import AIResponseLanguage, JobAnalysisPayload, JobAnalysisRequest, JobRead, JobStatus
from app.services.job_preprocessing import clean_description
from app.services.response_language import language_instruction, normalize_language


MAX_LIST_ITEMS = 5
MAX_ITEM_CHARS = 80
MAX_SUMMARY_CHARS = 240
JOB_ANALYSIS_MAX_TOKENS = 1000
logger = logging.getLogger(__name__)


class LeanJobAnalysisSignature(dspy.Signature):
    """Analyze one specific job posting and return concise, actionable guidance only.

    Relevance Rule:
    - Include only information that directly helps the candidate:
        1) understand real requirements,
        2) improve the CV for this role,
        3) prepare for this exact interview/job,
        4) identify concrete skill gaps.
    - Do not include any information that is not directly actionable for getting this specific job.

    Hard prohibitions:
    - No motivational or generic coaching text.
    - No obvious statements (for example: "experience is important").
    - No long introductions or filler phrases.
    - Do not repeat job description text unless it is transformed into a specific action.
    - Do not mention technologies that are not explicitly present in the job text.

    Noise Filter (apply internally before final answer):
    - Remove generic advice.
    - Remove repeated ideas.
    - Remove irrelevant skills.
    - Remove vague suggestions.

    Format and tone:
    - Keep outputs short, direct, professional.
    - Use brief bullet-style items for list outputs.
    - No long paragraphs.
    """

    title: str = dspy.InputField(desc="Job title")
    company: str = dspy.InputField(desc="Company name")
    desc: str = dspy.InputField(desc="Cleaned job text")
    response_language: str = dspy.InputField(desc="Language instruction for all generated content")
    summary: str = dspy.OutputField(
        desc="Max 2 short sentences. Only role-specific actionable context. No intro/filler."
    )
    seniority: str = dspy.OutputField(desc="One label")
    role_type: str = dspy.OutputField(desc="One role family")
    req_skills: list[str] = dspy.OutputField(
        desc="Max 5 concrete strengths/requirements from the posting. Short bullet-style phrases only."
    )
    nice_skills: list[str] = dspy.OutputField(
        desc="Max 5 optional skills explicitly hinted by the posting. No irrelevant tech."
    )
    responsibilities: list[str] = dspy.OutputField(
        desc="Max 5 core tasks. Rewrite as concise bullet-style items, not copied text."
    )
    prep: list[str] = dspy.OutputField(
        desc="Max 5 direct preparation actions for this role. Short and actionable only."
    )
    learn: list[str] = dspy.OutputField(
        desc="Max 5 focused learning actions tied to missing requirements in this posting."
    )
    gaps: list[str] = dspy.OutputField(
        desc="Max 5 clear skill gaps for this job. Specific and concise; no vague advice."
    )
    resume: list[str] = dspy.OutputField(
        desc="Max 5 CV improvements for this job. Each item must be directly actionable."
    )
    interview: list[str] = dspy.OutputField(
        desc="Max 5 interview preparation recommendations for this role. Short explanations only."
    )
    projects: list[str] = dspy.OutputField(
        desc="Max 5 portfolio/recommendation items that increase fit for this exact role."
    )


class JobAnalyzerModule(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(LeanJobAnalysisSignature)

    def forward(
        self,
        title: str,
        company: str,
        description: str,
        response_language: str,
        max_tokens: int | None = None,
    ):
        if max_tokens is None:
            return self.predict(
                title=title,
                company=company,
                desc=description,
                response_language=response_language,
            )

        with dspy_lm_override(max_tokens=max_tokens):
            return self.predict(
                title=title,
                company=company,
                desc=description,
                response_language=response_language,
            )


class JobAnalyzerService:
    def __init__(self) -> None:
        settings = get_settings()
        self.analyzer: JobAnalyzerModule | None = None
        self.timeout_seconds = settings.ai_timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._cache: dict[str, JobAnalysisPayload] = {}

    def _get_analyzer(self) -> JobAnalyzerModule:
        if self.analyzer is None:
            try:
                configure_dspy()
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI analysis is not configured.",
                ) from exc
            self.analyzer = JobAnalyzerModule()
        return self.analyzer

    def analyze(
        self,
        payload: JobAnalysisRequest,
        session: Session | None = None,
        user: User | None = None,
    ) -> JobRead:
        cleaned_description = clean_description(payload.description)
        selected_language = normalize_language(payload.language)
        cache_key = _build_cache_key(payload.title, payload.company, cleaned_description, selected_language)

        if session is not None and user is not None and not payload.regenerate:
            stored = crud.get_matching_job_analysis(
                session,
                user_id=user.id,
                title=payload.title,
                company=payload.company,
                clean_description=cleaned_description,
            )
            if stored is not None and _analysis_language(stored.analysis_result) == selected_language:
                logger.info("ai_cache_reuse operation=job_analysis source=db job_id=%s", stored.id)
                response = JobAnalysisPayload(**stored.analysis_result)
                self._cache[cache_key] = response.model_copy(deep=True)
                return self._serialize_job(stored)

        cached = None if payload.regenerate else self._cache.get(cache_key)
        if cached is not None:
            logger.info("ai_cache_reuse operation=job_analysis source=memory")
            if session is not None and user is not None:
                stored = crud.create_job_analysis(
                    session,
                    user_id=user.id,
                    title=payload.title,
                    company=payload.company,
                    description=payload.description,
                    clean_description=cleaned_description,
                    analysis_result={**cached.model_dump(), "_language": selected_language},
                )
                return self._serialize_job(stored)

            return JobRead(
                id=0,
                title=payload.title,
                company=payload.company,
                description=payload.description,
                clean_description=cleaned_description,
                analysis_result=cached.model_copy(deep=True),
                created_at=None,
            )

        try:
            analyzer = self._get_analyzer()
            logger.info(
                "ai_call operation=job_analysis title=%s company=%s regenerate=%s",
                payload.title,
                payload.company,
                payload.regenerate,
            )
            result = run_ai_call_with_timeout(
                executor=self._executor,
                timeout_seconds=self.timeout_seconds,
                operation="job_analysis",
                logger=logger,
                callable_=analyzer,
                lm_max_tokens=JOB_ANALYSIS_MAX_TOKENS,
                title=payload.title,
                company=payload.company,
                description=cleaned_description,
                response_language=language_instruction(selected_language),
                max_tokens=JOB_ANALYSIS_MAX_TOKENS,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise build_ai_failure_http_exception(
                exc=exc,
                logger=logger,
                operation="job_analysis",
                default_detail="Failed to analyze job description. Please try again.",
            ) from exc

        response = JobAnalysisPayload(
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
        if session is not None and user is not None:
            if payload.regenerate:
                stored = crud.get_matching_job_analysis(
                    session,
                    user_id=user.id,
                    title=payload.title,
                    company=payload.company,
                    clean_description=cleaned_description,
                )
                if stored is not None:
                    stored = crud.update_job_analysis_result(
                        session,
                        stored,
                        {**response.model_dump(), "_language": selected_language},
                    )
                    self._cache[cache_key] = response.model_copy(deep=True)
                    return self._serialize_job(stored)

            stored = crud.create_job_analysis(
                session,
                user_id=user.id,
                title=payload.title,
                company=payload.company,
                description=payload.description,
                clean_description=cleaned_description,
                analysis_result={**response.model_dump(), "_language": selected_language},
            )
            self._cache[cache_key] = response.model_copy(deep=True)
            return self._serialize_job(stored)
        self._cache[cache_key] = response.model_copy(deep=True)
        return JobRead(
            id=0,
            title=payload.title,
            company=payload.company,
            description=payload.description,
            clean_description=cleaned_description,
            analysis_result=response,
            created_at=None,
        )

    def list_jobs(self, session: Session, user: User) -> list[JobRead]:
        return [self._serialize_job(job) for job in crud.get_jobs_for_user(session, user.id)]

    def get_job(self, session: Session, user: User, job_id: int) -> JobRead:
        job = crud.get_job_for_user(session, user.id, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")
        return self._serialize_job(job)

    def update_job_status(
        self,
        session: Session,
        user: User,
        job_id: int,
        status_value: JobStatus,
        applied_date: datetime | None,
    ) -> JobRead:
        job = crud.get_job_for_user(session, user.id, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")

        effective_applied_date = applied_date
        if status_value == "applied" and effective_applied_date is None and job.applied_date is None:
            effective_applied_date = datetime.now(timezone.utc)

        updated = crud.update_job_status(session, job, status_value, effective_applied_date)
        return self._serialize_job(updated)

    def update_job_notes(self, session: Session, user: User, job_id: int, notes: str | None) -> JobRead:
        job = crud.get_job_for_user(session, user.id, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")

        normalized_notes = notes.strip() if isinstance(notes, str) else None
        updated = crud.update_job_notes(session, job, normalized_notes or None)
        return self._serialize_job(updated)

    def _serialize_job(self, job) -> JobRead:
        return JobRead(
            id=job.id,
            title=job.title,
            company=job.company,
            description=job.description,
            clean_description=job.clean_description,
            analysis_result=JobAnalysisPayload(**job.analysis_result),
            status=job.status,
            applied_date=job.applied_date,
            notes=job.notes,
            created_at=job.created_at,
        )


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


def _build_cache_key(title: str, company: str, description: str, language: AIResponseLanguage) -> str:
    payload = f"{title.strip().lower()}|{company.strip().lower()}|{description.strip().lower()}|{language}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _analysis_language(analysis_result: dict) -> AIResponseLanguage:
    language = analysis_result.get("_language") if isinstance(analysis_result, dict) else None
    return normalize_language(language)


_service: JobAnalyzerService | None = None


def get_job_analyzer_service() -> JobAnalyzerService:
    global _service
    if _service is None:
        _service = JobAnalyzerService()
    return _service
