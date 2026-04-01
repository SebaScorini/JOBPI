import hashlib
import logging
import re
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
JOB_ANALYSIS_RETRY_DESCRIPTION_CHARS = 5000
SKILL_HINTS = [
    "python",
    "fastapi",
    "sql",
    "postgresql",
    "aws",
    "docker",
    "kubernetes",
    "typescript",
    "react",
    "node",
    "api",
    "backend",
]
logger = logging.getLogger(__name__)


class LeanJobAnalysisSignature(dspy.Signature):
    """Return concise, role-specific job guidance only.

    Keep only actionable content for requirements, CV improvements, prep, and gaps.
    Exclude filler, repeated ideas, generic claims, obvious statements, and irrelevant tech.
    """

    title: str = dspy.InputField(desc="Job title")
    company: str = dspy.InputField(desc="Company name")
    desc: str = dspy.InputField(desc="Cleaned job text")
    response_language: str = dspy.InputField(desc="Output language")
    summary: str = dspy.OutputField(desc="1-2 actionable sentences. No intro, filler, or copied JD text.")
    seniority: str = dspy.OutputField(desc="One label")
    role_type: str = dspy.OutputField(desc="One role family")
    req_skills: list[str] = dspy.OutputField(
        desc="Max 5 required skills from the posting. Short phrases only."
    )
    nice_skills: list[str] = dspy.OutputField(
        desc="Max 5 optional skills explicitly hinted in the posting."
    )
    responsibilities: list[str] = dspy.OutputField(
        desc="Max 5 core tasks rewritten as concise items; do not copy lines verbatim."
    )
    prep: list[str] = dspy.OutputField(
        desc="Max 5 preparation actions for this role. Actionable and specific."
    )
    learn: list[str] = dspy.OutputField(
        desc="Max 5 learning actions tied to missing requirements in this posting."
    )
    gaps: list[str] = dspy.OutputField(
        desc="Max 5 concrete skill gaps for this job. No vague or generic advice."
    )
    resume: list[str] = dspy.OutputField(
        desc="Max 5 CV improvements for this job. Each item must be directly actionable."
    )
    interview: list[str] = dspy.OutputField(
        desc="Max 5 interview focus points for this role. Short explanations only."
    )
    projects: list[str] = dspy.OutputField(
        desc="Max 5 portfolio project ideas that increase fit for this exact role."
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
        self.max_tokens = settings.job_analysis_max_tokens
        self.retry_max_tokens = settings.job_analysis_retry_max_tokens
        self.retry_description_chars = settings.job_preprocess_target_chars
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

        response: JobAnalysisPayload | None = None
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
                lm_max_tokens=self.max_tokens,
                title=payload.title,
                company=payload.company,
                description=cleaned_description,
                response_language=language_instruction(selected_language),
                max_tokens=self.max_tokens,
            )
            response = self._build_payload_from_result(result)
        except HTTPException as exc:
            if exc.status_code != status.HTTP_504_GATEWAY_TIMEOUT:
                logger.warning(
                    "ai_fallback operation=job_analysis reason=http_%s",
                    exc.status_code,
                )
                response = self._build_fallback_analysis_payload(
                    title=payload.title,
                    company=payload.company,
                    cleaned_description=cleaned_description,
                    language=selected_language,
                )
            else:
                retry_description = cleaned_description[:self.retry_description_chars]
                logger.warning(
                    "ai_retry operation=job_analysis reason=timeout retry_max_tokens=%s retry_desc_chars=%s",
                    self.retry_max_tokens,
                    len(retry_description),
                )
                try:
                    result = run_ai_call_with_timeout(
                        executor=self._executor,
                        timeout_seconds=max(self.timeout_seconds, 30),
                        operation="job_analysis_retry",
                        logger=logger,
                        callable_=analyzer,
                        lm_max_tokens=self.retry_max_tokens,
                        title=payload.title,
                        company=payload.company,
                        description=retry_description,
                        response_language=language_instruction(selected_language),
                        max_tokens=self.retry_max_tokens,
                    )
                    response = self._build_payload_from_result(result)
                except Exception as retry_exc:
                    logger.warning(
                        "ai_fallback operation=job_analysis reason=retry_failed error=%s",
                        type(retry_exc).__name__,
                    )
                    response = self._build_fallback_analysis_payload(
                        title=payload.title,
                        company=payload.company,
                        cleaned_description=retry_description,
                        language=selected_language,
                    )
        except Exception as exc:
            logger.warning("ai_fallback operation=job_analysis reason=exception", exc_info=exc)
            response = self._build_fallback_analysis_payload(
                title=payload.title,
                company=payload.company,
                cleaned_description=cleaned_description,
                language=selected_language,
            )

        if response is None:
            raise build_ai_failure_http_exception(
                exc=RuntimeError("job_analysis_response_not_generated"),
                logger=logger,
                operation="job_analysis",
                default_detail="Failed to analyze job description. Please try again.",
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

    def _build_payload_from_result(self, result: object) -> JobAnalysisPayload:
        return JobAnalysisPayload(
            summary=_normalize_text(getattr(result, "summary", ""), MAX_SUMMARY_CHARS),
            seniority=_normalize_text(getattr(result, "seniority", ""), 40),
            role_type=_normalize_text(getattr(result, "role_type", ""), 40),
            required_skills=_normalize_list(getattr(result, "req_skills", [])),
            nice_to_have_skills=_normalize_list(getattr(result, "nice_skills", [])),
            responsibilities=_normalize_list(getattr(result, "responsibilities", [])),
            how_to_prepare=_normalize_list(getattr(result, "prep", [])),
            learning_path=_normalize_list(getattr(result, "learn", [])),
            missing_skills=_normalize_list(getattr(result, "gaps", [])),
            resume_tips=_normalize_list(getattr(result, "resume", [])),
            interview_tips=_normalize_list(getattr(result, "interview", [])),
            portfolio_project_ideas=_normalize_list(getattr(result, "projects", [])),
        )

    def _build_fallback_analysis_payload(
        self,
        *,
        title: str,
        company: str,
        cleaned_description: str,
        language: AIResponseLanguage,
    ) -> JobAnalysisPayload:
        text = cleaned_description.lower()
        extracted_skills = [skill for skill in SKILL_HINTS if re.search(rf"\\b{re.escape(skill)}\\b", text)]

        sentence_candidates = [
            line.strip(" -")
            for line in re.split(r"[\\n\\.]+", cleaned_description)
            if line.strip()
        ]
        actionable = [s for s in sentence_candidates if any(k in s.lower() for k in ("build", "develop", "design", "manage", "api", "service"))]

        summary = (
            f"Fallback analysis for {title} at {company}: extracted key role requirements from the description."
            if language == "english"
            else f"Analisis alternativo para {title} en {company}: se extrajeron requisitos clave del puesto."
        )

        responsibilities = _normalize_list(actionable[:MAX_LIST_ITEMS])
        if not responsibilities:
            responsibilities = _normalize_list(sentence_candidates[:MAX_LIST_ITEMS])

        required_skills = _normalize_list(extracted_skills[:MAX_LIST_ITEMS])
        if not required_skills:
            required_skills = ["Communication", "Problem solving"] if language == "english" else ["Comunicacion", "Resolucion de problemas"]

        prep = (
            [
                "Map your experience to each required skill.",
                "Prepare two measurable impact examples.",
                "Review architecture and API design decisions.",
            ]
            if language == "english"
            else [
                "Relaciona tu experiencia con cada habilidad requerida.",
                "Prepara dos ejemplos con impacto medible.",
                "Repasa decisiones de arquitectura y diseno de APIs.",
            ]
        )

        return JobAnalysisPayload(
            summary=summary,
            seniority="mid",
            role_type="generalist",
            required_skills=required_skills,
            nice_to_have_skills=[],
            responsibilities=responsibilities,
            how_to_prepare=_normalize_list(prep),
            learning_path=[],
            missing_skills=[],
            resume_tips=_normalize_list(prep[:2]),
            interview_tips=_normalize_list(prep[1:]),
            portfolio_project_ideas=[],
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
