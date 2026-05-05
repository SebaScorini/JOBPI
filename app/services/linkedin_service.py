from __future__ import annotations

# ruff: noqa: E402

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import logging

from app.core.runtime import configure_runtime_environment

configure_runtime_environment()

import dspy
from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.ai import (
    build_ai_failure_http_exception,
    dspy_lm_override,
    run_structured_ai_call,
    use_provider_fallback_model,
)
from app.core.config import configure_dspy, get_settings
from app.models import User
from app.models.ai_schemas import ColdOutreachAIOutput, LinkedInProfileAIOutput
from app.repositories import CvLibraryRepository, InterviewRepository, JobRepository
from app.schemas.job import AIResponseLanguage
from app.services.job_preprocessing import build_cv_context, build_job_context
from app.services.response_language import language_instruction, normalize_language


logger = logging.getLogger(__name__)
DEFAULT_LINKEDIN_MAX_TOKENS = 1800
DEFAULT_LINKEDIN_RETRY_MAX_TOKENS = 2200
MAX_LINKEDIN_TARGET_JOBS = 5


def _user_id(user: User) -> int:
    assert user.id is not None, "User.id must not be None for a persisted user"
    return user.id


class LinkedInProfileSignature(dspy.Signature):
    """Optimize LinkedIn headline and About copy using only the CV and target roles.

    Generate a profile that is specific, truthful, and grounded in the candidate evidence.
    Limit scope to a LinkedIn headline and About summary only. Do not rewrite experience.
    Do not use generic praise or flattery. Do not invent achievements not present in the CV.
    Do not use buzzwords like "synergy", "innovative", or "passionate" unless directly from
    the CV. Prefer concrete role keywords and proof points from the provided context.
    """

    cv_context: str = dspy.InputField(desc="Markdown CV context with the candidate's real evidence")
    target_roles: str = dspy.InputField(desc="Aggregated Markdown context from up to 5 saved target jobs")
    response_language: str = dspy.InputField(desc="Language for all generated profile text")
    headline: str = dspy.OutputField(desc="LinkedIn headline only. Maximum 220 characters.")
    about_summary: str = dspy.OutputField(
        desc=(
            "LinkedIn About summary only. Maximum 2600 characters. Use a human, specific tone, "
            "grounded in CV evidence and target-role overlap."
        )
    )
    keywords: list[str] = dspy.OutputField(desc="Return up to 10 concise LinkedIn/search keywords.")
    optimization_tips: list[str] = dspy.OutputField(
        desc="Return up to 5 practical profile optimization tips based on the CV and target roles."
    )


class ColdOutreachSignature(dspy.Signature):
    """Write a concise LinkedIn connection note grounded in the job and CV.

    Connection messages must be under 300 characters. Use only concrete overlaps between the
    candidate evidence and the role/company. Do not use generic praise or flattery. Do not invent
    achievements not present in the CV. Do not use buzzwords like "synergy", "innovative", or
    "passionate" unless directly from the CV.
    """

    job_context: str = dspy.InputField(desc="Markdown job context with the useful posting content")
    cv_context: str = dspy.InputField(desc="Markdown CV context with the candidate's strongest evidence")
    hiring_manager_name: str = dspy.InputField(desc="Optional hiring manager name, or empty string")
    response_language: str = dspy.InputField(desc="Language for all generated outreach text")
    connection_message: str = dspy.OutputField(
        desc="LinkedIn connection request note. Plain text only. Strictly 300 characters or fewer."
    )
    personalization_notes: list[str] = dspy.OutputField(
        desc="Return up to 3 short notes explaining why the chosen personalization points were used."
    )



class LinkedInProfileModule(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(LinkedInProfileSignature)

    def forward(
        self,
        *,
        cv_context: str,
        target_roles: str,
        response_language: str,
        max_tokens: int | None = None,
        model: str | None = None,
    ):
        if max_tokens is None:
            return self.predict(
                cv_context=cv_context,
                target_roles=target_roles,
                response_language=response_language,
            )

        with dspy_lm_override(max_tokens=max_tokens, model=model):
            return self.predict(
                cv_context=cv_context,
                target_roles=target_roles,
                response_language=response_language,
            )


class ColdOutreachModule(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(ColdOutreachSignature)

    def forward(
        self,
        *,
        job_context: str,
        cv_context: str,
        hiring_manager_name: str,
        response_language: str,
        max_tokens: int | None = None,
        model: str | None = None,
    ):
        if max_tokens is None:
            return self.predict(
                job_context=job_context,
                cv_context=cv_context,
                hiring_manager_name=hiring_manager_name,
                response_language=response_language,
            )

        with dspy_lm_override(max_tokens=max_tokens, model=model):
            return self.predict(
                job_context=job_context,
                cv_context=cv_context,
                hiring_manager_name=hiring_manager_name,
                response_language=response_language,
            )



class LinkedInService:
    def __init__(
        self,
        job_repository: JobRepository | None = None,
        cv_repository: CvLibraryRepository | None = None,
        interview_repository: InterviewRepository | None = None,
    ) -> None:
        settings = get_settings()
        self.profile_generator: LinkedInProfileModule | None = None
        self.outreach_generator: ColdOutreachModule | None = None
        self.timeout_seconds = settings.ai_timeout_seconds
        self.max_tokens = min(settings.job_analysis_max_tokens, DEFAULT_LINKEDIN_MAX_TOKENS)
        self.retry_max_tokens = min(settings.job_analysis_retry_max_tokens, DEFAULT_LINKEDIN_RETRY_MAX_TOKENS)
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._job_repository = job_repository or JobRepository()
        self._cv_repository = cv_repository or CvLibraryRepository()
        self._interview_repository = interview_repository or InterviewRepository()

    def _get_profile_generator(self) -> LinkedInProfileModule:
        if self.profile_generator is None:
            self._configure_ai()
            self.profile_generator = LinkedInProfileModule()
        return self.profile_generator

    def _get_outreach_generator(self) -> ColdOutreachModule:
        if self.outreach_generator is None:
            self._configure_ai()
            self.outreach_generator = ColdOutreachModule()
        return self.outreach_generator

    def _configure_ai(self) -> None:
        try:
            configure_dspy()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI analysis is not configured.",
            ) from exc

    def generate_linkedin_profile(
        self,
        session: Session,
        user: User,
        cv_id: int,
        job_ids: list[int] | None = None,
        language: AIResponseLanguage = "english",
        regenerate: bool = False,
    ) -> LinkedInProfileAIOutput:
        selected_language = normalize_language(language)
        cv = self._cv_repository.get_cv_for_user(session, _user_id(user), cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")

        jobs = self._load_target_jobs(session, user, job_ids or [])
        cache_key = _cache_key(language=selected_language, cv_id=cv_id, job_ids=[int(job.id) for job in jobs if job.id])
        cached = _get_cached_ai_output(cv.linkedin_profile_cache, cache_key, LinkedInProfileAIOutput)
        if cached is not None and not regenerate:
            logger.info("ai_cache_hit operation=linkedin_profile_generation cv_id=%s job_count=%s", cv_id, len(jobs))
            return cached

        cv_context = build_cv_context(cv.clean_text, summary=cv.summary, library_summary=cv.library_summary)
        target_roles = self._build_target_roles_context(jobs)

        try:
            generator = self._get_profile_generator()
            logger.info("ai_call operation=linkedin_profile_generation cv_id=%s job_count=%s", cv_id, len(jobs))
            parsed = run_structured_ai_call(
                schema=LinkedInProfileAIOutput,
                executor=self._executor,
                timeout_seconds=self.timeout_seconds,
                operation="linkedin_profile_generation",
                logger=logger,
                callable_=generator,
                lm_max_tokens=self.max_tokens,
                retry_lm_max_tokens=self.retry_max_tokens,
                attempt_kwargs_builder_with_exception=lambda attempt, previous_exception: {
                    "cv_context": cv_context,
                    "target_roles": target_roles,
                    "response_language": language_instruction(selected_language),
                    "max_tokens": self.max_tokens if attempt == 0 else self.retry_max_tokens,
                    "model": use_provider_fallback_model(attempt, previous_exception),
                },
            )
        except HTTPException as exc:
            logger.warning("ai_call_http_error operation=linkedin_profile_generation status_code=%s", exc.status_code)
            raise
        except Exception as exc:
            raise build_ai_failure_http_exception(
                exc=exc,
                logger=logger,
                operation="linkedin_profile_generation",
                default_detail="Failed to generate LinkedIn profile content. Please try again.",
            ) from exc

        updated_cache = _updated_cache(cv.linkedin_profile_cache, cache_key, parsed.payload.model_dump())
        self._cv_repository.update_linkedin_profile_cache(session, cv, updated_cache)
        return parsed.payload

    def get_cached_linkedin_profile(
        self,
        session: Session,
        user: User,
        cv_id: int,
        job_ids: list[int] | None = None,
        language: AIResponseLanguage = "english",
    ) -> LinkedInProfileAIOutput | None:
        selected_language = normalize_language(language)
        cv = self._cv_repository.get_cv_for_user(session, _user_id(user), cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")
        jobs = self._load_target_jobs(session, user, job_ids or [])
        cache_key = _cache_key(language=selected_language, cv_id=cv_id, job_ids=[int(job.id) for job in jobs if job.id])
        return _get_cached_ai_output(cv.linkedin_profile_cache, cache_key, LinkedInProfileAIOutput)

    def generate_cold_outreach(
        self,
        session: Session,
        user: User,
        job_id: int,
        cv_id: int,
        hiring_manager_name: str | None = None,
        language: AIResponseLanguage = "english",
        regenerate: bool = False,
    ) -> ColdOutreachAIOutput:
        selected_language = normalize_language(language)
        job = self._job_repository.get_for_user(session, user_id=_user_id(user), job_id=job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")

        cv = self._cv_repository.get_cv_for_user(session, _user_id(user), cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")

        normalized_manager_name = " ".join((hiring_manager_name or "").split()).strip()
        cache_key = _cache_key(
            language=selected_language,
            cv_id=cv_id,
            job_id=job_id,
            hiring_manager_name=normalized_manager_name.lower(),
        )
        cached = _get_cached_ai_output(job.linkedin_outreach_cache, cache_key, ColdOutreachAIOutput)
        if cached is not None and not regenerate:
            logger.info("ai_cache_hit operation=cold_outreach_generation job_id=%s cv_id=%s", job_id, cv_id)
            return cached

        job_context = build_job_context(job.clean_description, title=job.title, company=job.company)
        cv_context = build_cv_context(cv.clean_text, summary=cv.summary, library_summary=cv.library_summary)

        try:
            generator = self._get_outreach_generator()
            logger.info("ai_call operation=cold_outreach_generation job_id=%s cv_id=%s", job_id, cv_id)
            parsed = run_structured_ai_call(
                schema=ColdOutreachAIOutput,
                executor=self._executor,
                timeout_seconds=self.timeout_seconds,
                operation="cold_outreach_generation",
                logger=logger,
                callable_=generator,
                lm_max_tokens=self.max_tokens,
                retry_lm_max_tokens=self.retry_max_tokens,
                attempt_kwargs_builder_with_exception=lambda attempt, previous_exception: {
                    "job_context": job_context,
                    "cv_context": cv_context,
                    "hiring_manager_name": normalized_manager_name,
                    "response_language": language_instruction(selected_language),
                    "max_tokens": self.max_tokens if attempt == 0 else self.retry_max_tokens,
                    "model": use_provider_fallback_model(attempt, previous_exception),
                },
            )
        except HTTPException as exc:
            logger.warning("ai_call_http_error operation=cold_outreach_generation status_code=%s", exc.status_code)
            raise
        except Exception as exc:
            raise build_ai_failure_http_exception(
                exc=exc,
                logger=logger,
                operation="cold_outreach_generation",
                default_detail="Failed to generate cold outreach message. Please try again.",
            ) from exc

        updated_cache = _updated_cache(job.linkedin_outreach_cache, cache_key, parsed.payload.model_dump())
        self._job_repository.update_linkedin_outreach_cache(session, job=job, cache=updated_cache)
        return parsed.payload

    def get_cached_cold_outreach(
        self,
        session: Session,
        user: User,
        job_id: int,
        cv_id: int,
        hiring_manager_name: str | None = None,
        language: AIResponseLanguage = "english",
    ) -> ColdOutreachAIOutput | None:
        selected_language = normalize_language(language)
        job = self._job_repository.get_for_user(session, user_id=_user_id(user), job_id=job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")
        cv = self._cv_repository.get_cv_for_user(session, _user_id(user), cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")
        normalized_manager_name = " ".join((hiring_manager_name or "").split()).strip()
        cache_key = _cache_key(
            language=selected_language,
            cv_id=cv_id,
            job_id=job_id,
            hiring_manager_name=normalized_manager_name.lower(),
        )
        return _get_cached_ai_output(job.linkedin_outreach_cache, cache_key, ColdOutreachAIOutput)

    def _load_target_jobs(self, session: Session, user: User, job_ids: list[int]) -> list[object]:
        user_id = _user_id(user)
        if not job_ids:
            jobs, _ = self._job_repository.list_for_user(
                session,
                user_id=user_id,
                limit=MAX_LINKEDIN_TARGET_JOBS,
                offset=0,
                is_saved=True,
            )
            return list(jobs)

        jobs = []
        for job_id in _dedupe_ints(job_ids)[:MAX_LINKEDIN_TARGET_JOBS]:
            job = self._job_repository.get_for_user(session, user_id=user_id, job_id=job_id)
            if job is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")
            jobs.append(job)
        return jobs

    def _build_target_roles_context(self, jobs: list[object]) -> str:
        if not jobs:
            return "No target job context was selected. Optimize from the CV evidence only."

        sections = []
        for index, job in enumerate(jobs, start=1):
            title = str(getattr(job, "title", "") or "").strip()
            company = str(getattr(job, "company", "") or "").strip()
            clean_description = str(getattr(job, "clean_description", "") or "")
            context = build_job_context(clean_description, title=title, company=company, max_chars=3000)
            sections.append(f"## Target Role {index}\n{context}")
        return "\n\n".join(sections).strip()

    def _load_interview_context(self, session: Session, user: User, job_id: int, session_id: int | None) -> str:
        if session_id is None:
            return ""

        interview_session = self._interview_repository.get_session_for_user(
            session,
            user_id=_user_id(user),
            session_id=session_id,
        )
        if interview_session is None or interview_session.job_id != job_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview session not found.")

        return _format_interview_context(
            interview_session=interview_session,
            questions=list(interview_session.questions or []),
            answers=list(interview_session.answers or []),
            evaluations=list(interview_session.evaluations or []),
        )


def _format_interview_context(*, interview_session: object, questions: list[dict], answers: list[dict], evaluations: list[dict]) -> str:
    if not questions and not answers and not evaluations:
        return ""

    import json

    summary = getattr(interview_session, "summary", None)
    overall_score = getattr(interview_session, "overall_score", None)
    answer_map = {int(item.get("question_index", -1)): item for item in answers if isinstance(item, dict)}
    evaluation_map = {int(item.get("question_index", -1)): item for item in evaluations if isinstance(item, dict)}

    interview_data = {
        "type": "simulated_mock_interview",
        "note": "This is an AI-generated mock interview. Use it as coaching input, not as a real recruiter thread.",
        "overall_score": overall_score,
        "summary": summary if isinstance(summary, dict) else None,
        "question_rounds": []
    }

    for index, question in enumerate(questions[:7]):
        if not isinstance(question, dict):
            continue
        question_text = str(question.get("question", "")).strip()
        if not question_text:
            continue

        round_data = {
            "index": index + 1,
            "question": question_text,
            "answer": "",
            "feedback": ""
        }

        answer = answer_map.get(index)
        if answer:
            answer_text = str(answer.get("answer_text", "")).strip()
            if answer_text:
                round_data["answer"] = answer_text[:1200]

        evaluation = evaluation_map.get(index)
        if evaluation:
            feedback = str(evaluation.get("feedback", "")).strip()
            if feedback:
                round_data["feedback"] = feedback[:800]

        interview_data["question_rounds"].append(round_data)

    return json.dumps(interview_data, ensure_ascii=False)


def _dedupe_ints(values: list[int]) -> list[int]:
    seen: set[int] = set()
    result: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _cache_key(**parts: object) -> str:
    normalized = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _get_cached_ai_output(cache: object, cache_key: str, schema):
    if not isinstance(cache, dict):
        return None
    payload = cache.get(cache_key)
    if not isinstance(payload, dict):
        return None
    try:
        return schema.model_validate(payload)
    except Exception:
        return None


def _updated_cache(cache: object, cache_key: str, payload: dict) -> dict:
    normalized = dict(cache) if isinstance(cache, dict) else {}
    normalized[cache_key] = payload
    return normalized


_service: LinkedInService | None = None


def get_linkedin_service() -> LinkedInService:
    global _service
    if _service is None:
        _service = LinkedInService()
    return _service
