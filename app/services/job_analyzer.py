import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from app.core.runtime import configure_runtime_environment

configure_runtime_environment()

import dspy
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.core.ai import (
    build_ai_failure_http_exception,
    dspy_lm_override,
    run_structured_ai_call,
    use_provider_fallback_model,
)
from app.core.config import configure_dspy, get_settings
from app.db import crud
from app.models.ai_schemas import JobAnalysisAIOutput
from app.models import User
from app.schemas.job import (
    AIResponseLanguage,
    JobAnalysisPayload,
    JobAnalysisRequest,
    JobDeleteResponse,
    JobRead,
    JobStatus,
)
from app.services.job_preprocessing import build_job_context, clean_description
from app.services.response_language import language_instruction, normalize_language


MAX_LIST_ITEMS = 6
MAX_ITEM_CHARS = 140
MAX_SUMMARY_CHARS = 420
JOB_ANALYSIS_RETRY_DESCRIPTION_CHARS = 5000
NON_SIGNAL_ITEM_WORDS = {
    "candidate",
    "concrete",
    "focus",
    "interview",
    "learn",
    "learning",
    "portfolio",
    "prepare",
    "project",
    "projects",
    "resume",
    "role",
    "skills",
    "specific",
    "tips",
}
SKILL_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("Retool", ("retool",)),
    ("SQL", ("sql", "postgresql", "mysql", "presto")),
    ("JavaScript", ("javascript", "js ")),
    ("TypeScript", ("typescript",)),
    ("Python", ("python",)),
    ("React", ("react",)),
    ("Node.js", ("node.js", "nodejs", " node ")),
    ("APIs", (" api", "apis", "restful api", "rest api")),
    ("Data migration", ("data migration", "migrate data", "migration project")),
    ("Data modernization", ("data modernization", "modernization")),
    ("Data modeling", ("data modeling", "data model")),
    ("Batch processing", ("batch",)),
    ("Streaming pipelines", ("streaming",)),
    ("Data governance", ("data governance", "apache ranger", "immuta", "unity catalog")),
    ("Data quality", ("great expectations", "data quality")),
    ("Datadog", ("datadog",)),
    ("AWS", ("aws",)),
    ("GCP", ("gcp", "google cloud")),
    ("Apache Spark", ("apache spark", " spark ")),
    ("Databricks", ("databricks",)),
    ("EMR", ("emr",)),
    ("Jira", ("jira",)),
    ("Confluence", ("confluence",)),
    ("Notion", ("notion",)),
    ("Compliance", ("compliance", "regulated", "regulatory", "banking environment")),
]
ROLE_TYPE_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("data", ("databricks", "spark", "data migration", "data modernization", "data engineering")),
    ("full-stack", ("full stack", "front-end and back-end", "frontend and backend")),
    ("frontend", ("frontend", "front-end", "ui", "ux")),
    ("backend", ("backend", "back-end", "api", "services")),
    ("analytics", ("analytics", "business intelligence", "data visibility")),
    ("operations", ("operational workflow", "operations", "automation")),
]
logger = logging.getLogger(__name__)
FALLBACK_ANALYSIS_MARKER = "_fallback"


class LeanJobAnalysisSignature(dspy.Signature):
    """Extract only the most decision-useful guidance from this job posting.

    Base every field on explicit evidence in the posting or a very strong role-level inference.
    Prefer the concrete requirements, responsibilities, tools, seniority, and outcomes that will
    help a candidate prepare. Be specific, but do not pad, repeat, generalize, or copy long
    fragments from the posting. Prefer sharp, useful synthesis over longer text.
    Do not use generic buzzwords, vague career advice, unsupported claims, or tech-only framing
    when the posting is clearly non-technical. Do not repeat the prompt, do not restate section
    labels, and do not collapse distinct insights into generic filler.
    Keep each output section meaningfully distinct: responsibilities should describe the work,
    prep should focus on what to practice or gather, learning_path should focus on skills to build,
    resume should focus on CV edits, interview should focus on live discussion topics, and projects
    should propose portfolio ideas. Avoid reusing the same wording pattern across sections.
    """

    title: str = dspy.InputField(desc="Job title for role framing")
    company: str = dspy.InputField(desc="Company name for context only")
    desc: str = dspy.InputField(desc="Cleaned, high-signal job description with requirements and responsibilities")
    response_language: str = dspy.InputField(desc="Language for every output field")
    summary: str = dspy.OutputField(
        desc="1-2 concise sentences explaining what the role most needs, what success likely looks like, and one concrete signal that makes the role distinctive. Grounded only in the posting."
    )
    seniority: str = dspy.OutputField(
        desc="Single label such as junior, mid, senior, lead, or unknown. Use unknown if the level is not reasonably clear."
    )
    role_type: str = dspy.OutputField(
        desc="Single short role family such as backend, full-stack, frontend, data, devops, mobile, qa, product, or generalist."
    )
    req_skills: list[str] = dspy.OutputField(
        desc="Max 5 must-have skills, tools, or knowledge areas explicitly required or strongly implied as core. Short, high-signal phrases only. Avoid repeating role family or obvious duplicates."
    )
    nice_skills: list[str] = dspy.OutputField(
        desc="Max 5 preferred or bonus skills that are helpful but not clearly mandatory. Only include items supported by the posting."
    )
    responsibilities: list[str] = dspy.OutputField(
        desc="Max 5 core responsibilities rewritten into concise action-first items. Preserve meaning, remove boilerplate, and mention the real scope, systems, or stakeholders when the posting provides them."
    )
    prep: list[str] = dspy.OutputField(
        desc="Max 4 concrete preparation actions for applying or interviewing well for this specific role. Focus on what to study, practice, or gather before applying. Make each action role-specific and avoid generic advice like 'review the stack' or 'prepare examples'."
    )
    learn: list[str] = dspy.OutputField(
        desc="Max 4 focused learning priorities that would close common gaps for this exact posting. These should be skill-building priorities tied to tools, domains, or delivery expectations in the posting, not interview prep or resume edits."
    )
    gaps: list[str] = dspy.OutputField(
        desc="Max 5 concrete candidate gaps suggested by the posting's expectations. Mention only requirements that appear important for fit."
    )
    resume: list[str] = dspy.OutputField(
        desc="Max 4 resume improvements that would better align a CV to this role. Each item must be directly actionable and role-specific. Focus only on CV content, ordering, and proof, and name the kind of evidence that should be added."
    )
    interview: list[str] = dspy.OutputField(
        desc="Max 4 interview focus points the candidate should prepare for, based on the role's scope, tools, and expected outcomes. These are live discussion topics with concrete angles or tradeoffs, not resume edits or general prep reminders."
    )
    projects: list[str] = dspy.OutputField(
        desc="Max 3 portfolio or project ideas that would increase fit for this exact role. Make them realistic, specific, and relevant to the posting, with a deliverable or scope that clearly differs from the learning and interview sections."
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
        model: str | None = None,
    ):
        if max_tokens is None:
            return self.predict(
                title=title,
                company=company,
                desc=description,
                response_language=response_language,
            )

        with dspy_lm_override(max_tokens=max_tokens, model=model):
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
        self._executor = ThreadPoolExecutor(max_workers=4)

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
        prompt_description = build_job_context(
            cleaned_description,
            title=payload.title,
            company=payload.company,
        )
        selected_language = normalize_language(payload.language)
        if session is not None and user is not None and not payload.regenerate:
            stored = crud.get_matching_job_analysis(
                session,
                user_id=user.id,
                title=payload.title,
                company=payload.company,
                clean_description=cleaned_description,
            )
            if stored is not None and _analysis_language(stored.analysis_result) != selected_language:
                stored = None

        response: JobAnalysisPayload | None = None
        try:
            analyzer = self._get_analyzer()
            logger.info(
                "ai_call operation=job_analysis title=%s company=%s regenerate=%s",
                payload.title,
                payload.company,
                payload.regenerate,
            )
            parsed = run_structured_ai_call(
                schema=JobAnalysisAIOutput,
                executor=self._executor,
                timeout_seconds=self.timeout_seconds,
                operation="job_analysis",
                logger=logger,
                callable_=analyzer,
                lm_max_tokens=self.max_tokens,
                retry_lm_max_tokens=self.retry_max_tokens,
                attempt_kwargs_builder_with_exception=lambda attempt, previous_exception: {
                    "title": payload.title,
                    "company": payload.company,
                    "description": prompt_description,
                    "response_language": language_instruction(selected_language),
                    "max_tokens": self.max_tokens if attempt == 0 else self.retry_max_tokens,
                    "model": use_provider_fallback_model(attempt, previous_exception),
                },
            )
            response = self._build_payload_from_result(parsed.payload)
            if not _is_meaningful_job_analysis_payload(response):
                logger.warning("ai_invalid_output operation=job_analysis reason=low_quality_output")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(
                        "The AI returned a low-quality job analysis. "
                        "Please try again with the AI provider available."
                    ),
                )
        except HTTPException as exc:
            if exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE and exc.detail == "AI analysis is not configured.":
                logger.warning("ai_call_http_error operation=job_analysis status_code=%s", exc.status_code)
                raise
            logger.warning(
                "ai_fallback operation=job_analysis reason=http_exception status_code=%s",
                exc.status_code,
            )
            response = self._build_fallback_analysis_payload(
                title=payload.title,
                company=payload.company,
                cleaned_description=cleaned_description,
                language=selected_language,
            )
        except Exception as exc:
            http_error = build_ai_failure_http_exception(
                exc=exc,
                logger=logger,
                operation="job_analysis",
                default_detail="Failed to analyze job description. Please try again.",
            )
            if http_error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE and http_error.detail == "AI analysis is not configured.":
                raise http_error
            logger.warning(
                "ai_fallback operation=job_analysis reason=exception status_code=%s",
                http_error.status_code,
            )
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
                        _serialize_job_analysis_result(response, selected_language),
                    )
                    return self._serialize_job(stored)

            if stored is not None:
                stored = crud.update_job_analysis_result(
                    session,
                    stored,
                    _serialize_job_analysis_result(response, selected_language),
                )
            else:
                stored = crud.create_job_analysis(
                    session,
                    user_id=user.id,
                    title=payload.title,
                    company=payload.company,
                    description=payload.description,
                    clean_description=cleaned_description,
                    analysis_result=_serialize_job_analysis_result(response, selected_language),
                )
            return self._serialize_job(stored)
        return JobRead(
            id=0,
            title=payload.title,
            company=payload.company,
            description=payload.description,
            clean_description=cleaned_description,
            analysis_result=response,
            created_at=None,
        )

    def list_jobs(
        self,
        session: Session,
        user: User,
        *,
        limit: int = 20,
        offset: int = 0,
        is_saved: bool | None = None,
    ) -> tuple[list[JobRead], int]:
        jobs, total = crud.get_jobs_for_user(session, user.id, limit=limit, offset=offset, is_saved=is_saved)
        return [self._serialize_job(job) for job in jobs], total

    def get_job(self, session: Session, user: User, job_id: int) -> JobRead:
        job = crud.get_job_for_user(session, user.id, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")
        return self._serialize_job(job)

    def delete_job(self, session: Session, user: User, job_id: int) -> JobDeleteResponse:
        # Fetch by primary key first so we can distinguish missing records from ownership violations.
        job = crud.get_job_by_id(session, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")
        if job.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this job.",
            )

        try:
            crud.delete_job(session, job)
        except IntegrityError as exc:
            logger.exception("job_delete_failed job_id=%s user_id=%s", job_id, user.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete job.",
            ) from exc
        logger.info("job_deleted job_id=%s user_id=%s", job_id, user.id)
        return JobDeleteResponse(success=True)

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

    def toggle_job_saved(self, session: Session, user: User, job_id: int) -> JobRead:
        job = crud.get_job_for_user(session, user.id, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")

        updated = crud.update_job_saved(session, job, not bool(job.is_saved))
        return self._serialize_job(updated)

    def _serialize_job(self, job) -> JobRead:
        return JobRead(
            id=job.id,
            title=job.title,
            company=job.company,
            description=job.description,
            clean_description=job.clean_description,
            analysis_result=JobAnalysisPayload(**job.analysis_result),
            is_saved=bool(job.is_saved),
            status=job.status,
            applied_date=job.applied_date,
            notes=job.notes,
            created_at=job.created_at,
        )

    def _build_payload_from_result(self, result: object) -> JobAnalysisPayload:
        return _refine_job_analysis_payload(JobAnalysisPayload(
            summary=_normalize_summary_text(getattr(result, "summary", ""), MAX_SUMMARY_CHARS),
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
        ))

    def _build_fallback_analysis_payload(
        self,
        *,
        title: str,
        company: str,
        cleaned_description: str,
        language: AIResponseLanguage,
    ) -> JobAnalysisPayload:
        text = cleaned_description.lower()
        extracted_skills = _extract_fallback_skills(cleaned_description)

        sentence_candidates = [
            line.strip(" -")
            for line in re.split(r"[\n\.]+", cleaned_description)
            if line.strip()
        ]
        actionable = [s for s in sentence_candidates if _looks_actionable_fallback_sentence(s)]
        seniority = _infer_fallback_seniority(text)
        role_type = _infer_fallback_role_type(text)

        summary = _build_fallback_summary(
            title=title,
            company=company,
            cleaned_description=cleaned_description,
            extracted_skills=extracted_skills,
            seniority=seniority,
            role_type=role_type,
            language=language,
        )

        responsibilities = _normalize_list(_rewrite_fallback_responsibilities(actionable[:MAX_LIST_ITEMS]))
        if not responsibilities:
            responsibilities = _normalize_list(_rewrite_fallback_responsibilities(sentence_candidates[:MAX_LIST_ITEMS]))

        required_skills = _normalize_list(extracted_skills[:MAX_LIST_ITEMS])
        if not required_skills:
            required_skills = (
                ["Communication", "Problem solving"]
                if language == "english"
                else ["Comunicacion", "Resolucion de problemas"]
            )

        return JobAnalysisPayload(
            summary=summary,
            seniority=seniority,
            role_type=role_type,
            required_skills=required_skills,
            nice_to_have_skills=_build_fallback_nice_to_have(cleaned_description, required_skills, language),
            responsibilities=responsibilities,
            how_to_prepare=_build_fallback_prepare(required_skills, responsibilities, language),
            learning_path=_build_fallback_learning_path(cleaned_description, language),
            missing_skills=_build_fallback_missing_skills(cleaned_description, required_skills, language),
            resume_tips=_build_fallback_resume_tips(required_skills, responsibilities, language),
            interview_tips=_build_fallback_interview_tips(required_skills, responsibilities, language),
            portfolio_project_ideas=_build_fallback_projects(required_skills, responsibilities, language),
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
        return _clean_trailing_fragment(text)

    cutoff = text.rfind(" ", 0, limit)
    if cutoff < int(limit * 0.6):
        cutoff = limit
    return _clean_trailing_fragment(text[:cutoff])


def _clean_trailing_fragment(text: str) -> str:
    cleaned = text.rstrip(" ,;:")
    if not cleaned:
        return ""

    # Collapse endings like ").," or ").;" to ")" before parenthesis balancing.
    cleaned = re.sub(r"\)\s*[,;:.]+$", ")", cleaned)

    # Remove dangling abbreviations often produced when truncation lands on "(e.g.".
    cleaned = re.sub(r"(?:\(|\s)+(?:e\.g|i\.e)\.?$", "", cleaned, flags=re.IGNORECASE).rstrip(" ,;:")

    # If truncation leaves an unmatched opening parenthesis at the tail, drop that tail.
    if cleaned.count("(") > cleaned.count(")"):
        last_open = cleaned.rfind("(")
        last_close = cleaned.rfind(")")
        if last_open > last_close:
            cleaned = cleaned[:last_open].rstrip(" ,;:")
        cleaned = cleaned[:last_open].rstrip(" ,;:")

    # If there are more closing than opening parentheses, trim unmatched trailing ")".
    while cleaned.endswith(")") and cleaned.count(")") > cleaned.count("("):
        cleaned = cleaned[:-1].rstrip(" ,;:")

    return cleaned


def _normalize_summary_text(value: object, limit: int) -> str:
    text = _normalize_text(value, max(limit * 3, limit))
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
            if len(selected) >= 3:
                break

        if selected:
            return " ".join(selected).rstrip(" ,;:")

        return _truncate_summary_segment(sentences[0], limit)

    return _truncate_summary_segment(text, limit)


def _truncate_summary_segment(text: str, limit: int) -> str:
    if len(text) <= limit:
        return _clean_trailing_fragment(text)

    cutoff = max(
        text.rfind(". ", 0, limit),
        text.rfind("; ", 0, limit),
        text.rfind(": ", 0, limit),
        text.rfind(", ", 0, limit),
        text.rfind(" ", 0, limit),
    )
    if cutoff < int(limit * 0.6):
        cutoff = limit
    return _clean_trailing_fragment(text[:cutoff])


def _build_cache_key(title: str, company: str, description: str, language: AIResponseLanguage) -> str:
    return build_context_fingerprint("job_analysis", title, company, description, language)


def _serialize_job_analysis_result(payload: JobAnalysisPayload, language: AIResponseLanguage) -> dict[str, object]:
    data = {**payload.model_dump(), "_language": language}
    if _is_fallback_job_analysis_payload(payload):
        data[FALLBACK_ANALYSIS_MARKER] = True
    return data


def _analysis_language(analysis_result: dict) -> AIResponseLanguage:
    language = analysis_result.get("_language") if isinstance(analysis_result, dict) else None
    return normalize_language(language)


def _is_persisted_fallback_job_analysis(analysis_result: dict | object) -> bool:
    return bool(isinstance(analysis_result, dict) and analysis_result.get(FALLBACK_ANALYSIS_MARKER))


def _should_cache_job_analysis_payload(payload: JobAnalysisPayload) -> bool:
    return not _is_fallback_job_analysis_payload(payload)


def _is_fallback_job_analysis_payload(payload: JobAnalysisPayload) -> bool:
    formulaic_prefixes = (
        "prepare 2-3 stories",
        "prepara 2-3 historias",
        "move your strongest evidence",
        "lleva tu mejor evidencia",
        "expect detailed questions on",
        "espera preguntas especificas sobre",
        "build an internal operations dashboard",
        "construye un dashboard interno de operaciones",
    )
    summary = payload.summary.lower().strip()
    if "the posting emphasizes cross-functional delivery" in summary:
        return True
    if "el aviso enfatiza trabajo cross-functional" in summary:
        return True

    combined_lists = [
        *payload.how_to_prepare,
        *payload.resume_tips,
        *payload.interview_tips,
        *payload.portfolio_project_ideas,
    ]
    lowered_items = [item.lower().strip() for item in combined_lists if item.strip()]
    formulaic_hits = sum(
        any(item.startswith(prefix) for prefix in formulaic_prefixes)
        for item in lowered_items
    )
    return formulaic_hits >= 2


def _is_meaningful_job_analysis_payload(payload: JobAnalysisPayload) -> bool:
    # Require a non-trivial summary — a single word or placeholder is not enough.
    if len(payload.summary.strip()) < 20:
        return False
    # Count how many key lists have at least one item. We require 4 out of 6
    # (raised from 3/5) to catch partially-empty AI responses that previously
    # slipped through and stored incomplete data in the database.
    populated_lists = sum(
        1
        for items in (
            payload.required_skills,
            payload.responsibilities,
            payload.how_to_prepare,
            payload.resume_tips,
            payload.interview_tips,
            payload.learning_path,
        )
        if items
    )
    return populated_lists >= 4


def _refine_job_analysis_payload(payload: JobAnalysisPayload) -> JobAnalysisPayload:
    required_skills = _dedupe_job_items(payload.required_skills, limit=5)
    nice_to_have_skills = _dedupe_job_items(payload.nice_to_have_skills, limit=4, blocked_items=required_skills)
    responsibilities = _dedupe_job_items(payload.responsibilities, limit=4)
    how_to_prepare = _dedupe_job_items(
        payload.how_to_prepare,
        limit=4,
        blocked_items=responsibilities,
    )
    learning_path = _dedupe_job_items(
        payload.learning_path,
        limit=4,
        blocked_items=how_to_prepare,
    )
    missing_skills = _dedupe_job_items(payload.missing_skills, limit=4, blocked_items=required_skills)
    resume_tips = _dedupe_job_items(
        payload.resume_tips,
        limit=4,
        blocked_items=how_to_prepare + learning_path,
    )
    interview_tips = _dedupe_job_items(
        payload.interview_tips,
        limit=4,
        blocked_items=how_to_prepare + resume_tips,
    )
    portfolio_project_ideas = _dedupe_job_items(
        payload.portfolio_project_ideas,
        limit=3,
        blocked_items=learning_path + interview_tips,
    )
    return payload.model_copy(
        update={
            "required_skills": required_skills,
            "nice_to_have_skills": nice_to_have_skills,
            "responsibilities": responsibilities,
            "how_to_prepare": how_to_prepare,
            "learning_path": learning_path,
            "missing_skills": missing_skills,
            "resume_tips": resume_tips,
            "interview_tips": interview_tips,
            "portfolio_project_ideas": portfolio_project_ideas,
        }
    )


def _dedupe_job_items(
    items: list[str],
    *,
    limit: int,
    blocked_items: list[str] | None = None,
) -> list[str]:
    blocked_signatures = [_job_item_signature(item) for item in blocked_items or [] if item.strip()]
    kept: list[str] = []
    kept_signatures: list[set[str]] = []
    for item in items:
        normalized = _normalize_text(item, 180).strip()
        if not normalized:
            continue
        signature = _job_item_signature(normalized)
        if signature:
            if any(_job_signatures_overlap(signature, blocked) for blocked in blocked_signatures):
                continue
            if any(_job_signatures_overlap(signature, existing) for existing in kept_signatures):
                continue
            kept_signatures.append(signature)
        elif normalized in kept:
            continue
        kept.append(normalized)
        if len(kept) >= limit:
            break
    return kept


def _job_item_signature(value: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#.-]{2,}\b", value)
        if token.lower() not in NON_SIGNAL_ITEM_WORDS and len(token) >= 4
    }


def _job_signatures_overlap(left: set[str], right: set[str]) -> bool:
    if not left or not right:
        return False
    overlap = left & right
    return len(overlap) >= 2 or overlap == left or overlap == right


def _looks_actionable_fallback_sentence(value: str) -> bool:
    lowered = value.lower().strip()
    if not lowered:
        return False
    if lowered.startswith(("team structure", "ideal profile", "soft skills", "education")):
        return False
    return bool(
        re.search(
            r"\b(develop|design|build|maintain|integrate|optimize|participate|collaborate|implement|review|scale)\b",
            lowered,
        )
        or re.search(r"\b(translate|ensure|improve|contribute|deliver|support|automate|identify)\b", lowered)
        or re.search(r"\bapi(s)?\b", lowered)
        or re.search(r"\bservices?\b", lowered)
    )


def _extract_fallback_skills(cleaned_description: str) -> list[str]:
    lowered = f" {cleaned_description.lower()} "
    matches: list[str] = []
    for label, patterns in SKILL_PATTERNS:
        if any(pattern in lowered for pattern in patterns):
            matches.append(label)
        if len(matches) >= MAX_LIST_ITEMS + 3:
            break
    return matches


def _infer_fallback_seniority(text: str) -> str:
    if re.search(r"\b(lead|principal|staff|architect)\b", text):
        return "lead"
    if re.search(r"\b(senior|5\+ years|6\+ years|7\+ years|8\+ years)\b", text):
        return "senior"
    if re.search(r"\b(4\+ years|mid|intermediate)\b", text):
        return "mid"
    if re.search(r"\b(junior|entry level|1\+ years|2\+ years)\b", text):
        return "junior"
    return "unknown"


def _infer_fallback_role_type(text: str) -> str:
    for label, patterns in ROLE_TYPE_PATTERNS:
        if any(pattern in text for pattern in patterns):
            return label
    return "generalist"


def _build_fallback_summary(
    *,
    title: str,
    company: str,
    cleaned_description: str,
    extracted_skills: list[str],
    seniority: str,
    role_type: str,
    language: AIResponseLanguage,
) -> str:
    responsibilities = _extract_summary_themes(cleaned_description)
    top_skills = ", ".join(extracted_skills[:3])
    if language == "english":
        opening = f"{company} is hiring a {seniority if seniority != 'unknown' else ''} {title}".replace("  ", " ").strip()
        if responsibilities and top_skills:
            return _normalize_summary_text(
                f"{opening} focused on {responsibilities[0]}. The strongest signals in the posting are {top_skills}, with success tied to {responsibilities[1] if len(responsibilities) > 1 else 'delivering reliable business-facing outcomes in a regulated environment'}.",
                MAX_SUMMARY_CHARS,
            )
        if top_skills:
            return _normalize_summary_text(
                f"{opening} with clear emphasis on {top_skills}. The role reads as a {role_type} position expected to improve operational efficiency and data visibility.",
                MAX_SUMMARY_CHARS,
            )
        return _normalize_summary_text(
            f"{opening}. The posting emphasizes cross-functional delivery, operational improvement, and clear execution in a structured environment.",
            MAX_SUMMARY_CHARS,
        )

    opening = f"{company} busca un perfil {seniority if seniority != 'unknown' else ''} para {title}".replace("  ", " ").strip()
    if responsibilities and top_skills:
        return _normalize_summary_text(
            f"{opening} con foco en {responsibilities[0]}. Las senales mas fuertes del aviso son {top_skills}, y el exito del rol depende de {responsibilities[1] if len(responsibilities) > 1 else 'entregar soluciones confiables para equipos de negocio en un entorno regulado'}.",
            MAX_SUMMARY_CHARS,
        )
    if top_skills:
        return _normalize_summary_text(
            f"{opening} con enfasis claro en {top_skills}. El puesto se parece a un rol {role_type} orientado a eficiencia operativa y visibilidad de datos.",
            MAX_SUMMARY_CHARS,
        )
    return _normalize_summary_text(
        f"{opening}. El aviso enfatiza trabajo cross-functional, mejora operativa y ejecucion prolija dentro de un entorno exigente.",
        MAX_SUMMARY_CHARS,
    )


def _extract_summary_themes(cleaned_description: str) -> list[str]:
    lowered = cleaned_description.lower()
    themes: list[str] = []
    if "mobile" in lowered or "react native" in lowered:
        themes.append("building reliable mobile or cross-platform product experiences")
    if "desktop" in lowered:
        themes.append("shipping high-performance desktop application experiences")
    if "frontend" in lowered or "ui" in lowered or "ux" in lowered:
        themes.append("delivering polished user-facing experiences with strong product collaboration")
    if "operational workflow" in lowered or "automate operational workflows" in lowered:
        themes.append("building internal tools that automate operational workflows")
    if "data visibility" in lowered:
        themes.append("improving data visibility across business teams")
    if "integration" in lowered or "apis" in lowered or "databases" in lowered:
        themes.append("connecting product features with APIs, backend services, and external systems")
    if "regulated" in lowered or "banking" in lowered or "governance" in lowered:
        themes.append("meeting security, governance, and regulated-environment standards")
    return themes[:2]


def _build_fallback_nice_to_have(
    cleaned_description: str,
    required_skills: list[str],
    language: AIResponseLanguage,
) -> list[str]:
    lowered = cleaned_description.lower()
    preferred = _extract_optional_phrases(cleaned_description)
    suggestions = [item for item in preferred if item not in required_skills]
    if "certification" in lowered and not any("certification" in item.lower() for item in suggestions):
        suggestions.append("Databricks certification" if "databricks" in lowered else ("Relevant certification" if language == "english" else "Certificacion relevante"))
    return _normalize_list(suggestions[:MAX_LIST_ITEMS])


def _extract_optional_phrases(cleaned_description: str) -> list[str]:
    matches: list[str] = []
    for raw_line in cleaned_description.splitlines():
        line = " ".join(raw_line.split()).strip(" -")
        lowered = line.lower()
        if not line:
            continue
        if any(marker in lowered for marker in ("plus", "nice to have", "preferred", "strong plus")):
            matches.append(line)
    return matches


def _build_fallback_prepare(
    required_skills: list[str],
    responsibilities: list[str],
    language: AIResponseLanguage,
) -> list[str]:
    top_skills = ", ".join(required_skills[:3]) if required_skills else ""
    top_responsibility = _compress_focus_area(responsibilities[0] if responsibilities else "")
    if language == "english":
        tips = [
            f"Prepare 2-3 stories that show direct ownership of {top_responsibility.lower()}." if top_responsibility else "Prepare 2-3 stories showing direct ownership of similar business-critical work.",
            f"Map your strongest evidence to {top_skills} with concrete tools, scale, and outcomes." if top_skills else "Map your strongest evidence to the role's core technical requirements with concrete outcomes.",
            "Be ready to explain how you worked with stakeholders, handled ambiguity, and shipped reliably under deadlines.",
            "Review one end-to-end delivery example: problem, constraints, solution, and measurable impact.",
            "Practice explaining complex technical decisions in business language.",
        ]
    else:
        tips = [
            f"Prepara 2-3 historias que demuestren ownership directo sobre {top_responsibility.lower()}." if top_responsibility else "Prepara 2-3 historias con ownership real sobre trabajo critico similar.",
            f"Relaciona tu mejor evidencia con {top_skills} usando herramientas, escala y resultados concretos." if top_skills else "Relaciona tu mejor evidencia con los requisitos tecnicos centrales usando resultados concretos.",
            "Practica como colaboraste con stakeholders, resolviste ambiguedad y entregaste bien bajo deadlines.",
            "Repasa un proyecto de punta a punta: problema, restricciones, solucion e impacto medible.",
            "Practica explicar decisiones tecnicas complejas en lenguaje de negocio.",
        ]
    return _normalize_list(tips)


def _build_fallback_learning_path(cleaned_description: str, language: AIResponseLanguage) -> list[str]:
    lowered = cleaned_description.lower()
    items: list[str] = []
    if "retool" in lowered:
        items.append("Deepen Retool app patterns for secure internal tooling." if language == "english" else "Profundiza patrones de Retool para internal tools seguros.")
    if "databricks" in lowered or "spark" in lowered:
        items.append("Refresh Databricks and Spark workflows for transformations and platform operations." if language == "english" else "Refuerza Databricks y Spark para transformaciones y operacion de plataforma.")
    if "governance" in lowered or "regulated" in lowered:
        items.append("Study practical data governance controls, lineage, and access policies in regulated environments." if language == "english" else "Estudia controles practicos de data governance, lineage y access policies en entornos regulados.")
    if "datadog" in lowered:
        items.append("Review monitoring and observability patterns in Datadog." if language == "english" else "Repasa patrones de monitoreo y observabilidad en Datadog.")
    if "sql" in lowered:
        items.append("Sharpen advanced SQL for analytics, debugging, and data validation." if language == "english" else "Mejora SQL avanzado para analitica, debugging y validacion de datos.")
    return _normalize_list(items)


def _build_fallback_missing_skills(
    cleaned_description: str,
    required_skills: list[str],
    language: AIResponseLanguage,
) -> list[str]:
    lowered = cleaned_description.lower()
    items: list[str] = []
    if "retool" in lowered and "Retool" in required_skills:
        items.append("Retool delivery in production internal tools." if language == "english" else "Experiencia real con Retool en internal tools productivos.")
    if "data migration" in lowered or "modernization" in lowered:
        items.append("Visible ownership of data migration or modernization programs." if language == "english" else "Ownership visible en proyectos de migracion o modernizacion de datos.")
    if "regulated" in lowered or "governance" in lowered:
        items.append("Examples of working under strict governance, security, or compliance controls." if language == "english" else "Ejemplos de trabajo bajo controles estrictos de governance, seguridad o compliance.")
    if "databricks" in lowered:
        items.append("Hands-on Databricks evidence, ideally with certification or platform operations." if language == "english" else "Evidencia concreta con Databricks, idealmente con certificacion u operacion de plataforma.")
    if "stakeholder" in lowered or "business" in lowered:
        items.append("Clear business-facing communication examples tied to technical delivery." if language == "english" else "Ejemplos claros de comunicacion con negocio ligados a entrega tecnica.")
    return _normalize_list(items)


def _build_fallback_resume_tips(
    required_skills: list[str],
    responsibilities: list[str],
    language: AIResponseLanguage,
) -> list[str]:
    top_skills = ", ".join(required_skills[:4]) if required_skills else "the role's core stack"
    top_responsibility = _compress_focus_area(responsibilities[0] if responsibilities else "business-critical internal tools")
    if language == "english":
        items = [
            f"Move your strongest evidence for {top_skills} into the summary and most recent experience section.",
            f"Rewrite bullets to show scope, stakeholders, and measurable outcomes for {top_responsibility.lower()}.",
            "Name the tools, frameworks, APIs, and platforms you used instead of describing them generically.",
            "Highlight delivery, optimization, debugging, or automation work with numbers: speed, adoption, reliability, or time saved.",
            "If you have cross-functional product or production support experience, make that explicit rather than implied.",
        ]
    else:
        items = [
            f"Lleva tu mejor evidencia de {top_skills} al resumen y a la experiencia mas reciente.",
            f"Reescribe bullets mostrando alcance, stakeholders e impacto medible sobre {top_responsibility.lower()}.",
            "Nombra herramientas, frameworks, APIs y plataformas concretas en vez de describirlas en general.",
            "Destaca trabajo de entrega, optimizacion, debugging o automatizacion con numeros: velocidad, adopcion, confiabilidad o tiempo ahorrado.",
            "Si trabajaste con producto, UX/UI o incidencias de produccion, dejalo explicito y no solo implicito.",
        ]
    return _normalize_list(items)


def _build_fallback_interview_tips(
    required_skills: list[str],
    responsibilities: list[str],
    language: AIResponseLanguage,
) -> list[str]:
    top_skills = ", ".join(required_skills[:3]) if required_skills else "core technical skills"
    top_responsibility = _compress_focus_area(responsibilities[0] if responsibilities else "internal platform delivery")
    if language == "english":
        items = [
            f"Expect detailed questions on {top_skills} and how you applied them in production.",
            f"Prepare to walk through a project centered on {top_responsibility.lower()}, including tradeoffs and stakeholder alignment.",
            "Have one example ready for debugging or quality decisions under real constraints.",
            "Be ready to discuss performance optimization, reliability, and production support after launch.",
            "Practice explaining why you chose a specific architecture, integration pattern, or data platform.",
        ]
    else:
        items = [
            f"Espera preguntas especificas sobre {top_skills} y como lo aplicaste en produccion.",
            f"Preparate para recorrer un proyecto enfocado en {top_responsibility.lower()}, incluyendo tradeoffs y alineacion con stakeholders.",
            "Ten listo un ejemplo sobre debugging o decisiones de calidad bajo restricciones reales.",
            "Repasa optimizacion de performance, confiabilidad y soporte en produccion despues del lanzamiento.",
            "Practica justificar por que elegiste una arquitectura, patron de integracion o data platform concreto.",
        ]
    return _normalize_list(items)


def _build_fallback_projects(
    required_skills: list[str],
    responsibilities: list[str],
    language: AIResponseLanguage,
) -> list[str]:
    required_joined = " ".join(required_skills).lower()
    data_focused = any(keyword in required_joined for keyword in ("databricks", "sql", "data", "spark"))
    frontend_focused = any(keyword in required_joined for keyword in ("react", "typescript", "next.js", "react native"))
    if language == "english":
        if frontend_focused:
            items = [
                "Build a cross-platform TypeScript app that consumes REST APIs with clear state management decisions.",
                "Ship a React or Next.js workflow with measurable performance and UX improvements.",
                "Create a production-style debugging case study showing how you diagnosed and fixed a real UI issue.",
                "Publish a small component or feature demo that highlights architecture, API integration, and code quality choices.",
            ]
        else:
            items = [
                "Build an internal operations dashboard that pulls from APIs and SQL sources, with role-based access and audit-friendly workflows.",
                "Create a migration case study showing how you modernized a reporting or data pipeline from legacy logic to a governed platform.",
                "Ship a Retool-style admin tool with approval flows, validation checks, and observability hooks." if "retool" in required_joined else "Ship an internal tool that automates approvals, validations, and operational follow-up.",
                "Publish a notebook or demo showing data quality checks, lineage decisions, and monitoring alerts." if data_focused else "Publish a case study highlighting governance, performance, and stakeholder outcomes.",
            ]
    else:
        if frontend_focused:
            items = [
                "Construye una app TypeScript cross-platform que consuma APIs REST y muestre decisiones claras de state management.",
                "Publica un flujo en React o Next.js con mejoras medibles de performance y UX.",
                "Arma un caso de debugging en produccion mostrando como encontraste y corregiste un bug real de UI.",
                "Comparte un demo pequeno que destaque arquitectura, integracion con APIs y decisiones de calidad de codigo.",
            ]
        else:
            items = [
                "Construye un dashboard interno de operaciones que consuma APIs y SQL, con accesos por rol y flujos auditables.",
                "Arma un case study de migracion mostrando como modernizaste reporting o pipelines desde logica legacy a una plataforma gobernada.",
                "Publica una herramienta estilo Retool con approval flows, validaciones y observabilidad." if "retool" in required_joined else "Publica una internal tool que automatice approvals, validaciones y seguimiento operativo.",
                "Comparte un notebook o demo con data quality checks, lineage y alertas de monitoreo." if data_focused else "Comparte un case study que destaque governance, performance e impacto en stakeholders.",
            ]
    return _normalize_list(items)


def _compress_focus_area(value: str) -> str:
    lowered = value.lower()
    if "operational workflow" in lowered:
        return "operational workflow automation"
    if "data visibility" in lowered:
        return "data visibility improvements"
    if "integration" in lowered or "apis" in lowered:
        return "system integrations"
    if "governance" in lowered or "regulated" in lowered:
        return "governed delivery in regulated environments"
    if not value:
        return ""
    return _normalize_text(value.lower(), 72)


def _rewrite_fallback_responsibilities(items: list[str]) -> list[str]:
    rewritten: list[str] = []
    for item in items:
        lowered = item.lower()
        if "retool" in lowered and "operational workflow" in lowered:
            rewritten.append("Build and deploy Retool applications that automate operational workflows and support business teams")
            continue
        if "data visibility" in lowered or "manual processes" in lowered:
            rewritten.append("Translate business needs into scalable internal tools that improve efficiency and data visibility")
            continue
        if "integrations" in lowered and ("apis" in lowered or "databases" in lowered):
            rewritten.append("Build integrations between Retool, APIs, databases, and third-party platforms")
            continue
        if "stakeholders" in lowered or "compliance" in lowered:
            rewritten.append("Partner with operations, compliance, and technology stakeholders to deliver high-impact automation")
            continue
        if "governance" in lowered or "regulated" in lowered:
            rewritten.append("Ensure delivery meets SDLC, security, and governance standards in regulated environments")
            continue
        rewritten.append(item)
    return rewritten


_service: JobAnalyzerService | None = None


def get_job_analyzer_service() -> JobAnalyzerService:
    global _service
    if _service is None:
        _service = JobAnalyzerService()
    return _service
