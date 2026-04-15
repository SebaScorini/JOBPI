import logging
from concurrent.futures import ThreadPoolExecutor
import re

from app.core.runtime import configure_runtime_environment

configure_runtime_environment()

import dspy
from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.ai import dspy_lm_override, looks_like_ai_auth_error, run_ai_call_with_circuit_breaker
from app.core.config import configure_dspy, get_settings
from app.db import crud
from app.models import User
from app.schemas.job import AIResponseLanguage
from app.services.job_analyzer import _normalize_text
from app.services.job_preprocessing import build_cv_excerpt, build_job_excerpt
from app.services.response_language import language_instruction, normalize_language


MAX_COVER_LETTER_CHARS = 1200
MAX_COVER_LETTER_PARAGRAPHS = 3
MAX_COVER_LETTER_PARAGRAPH_CHARS = 380
DEFAULT_COVER_LETTER_MAX_TOKENS = 480
logger = logging.getLogger(__name__)
WORD_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+#.-]{1,}\b")


class CoverLetterSignature(dspy.Signature):
    """Write a concise cover letter grounded in the job needs and the candidate's real evidence.

    Use only claims that are supported by the CV summary or CV excerpt. Emphasize the most
    relevant matches to the role, sound human and specific, and avoid filler, flattery,
    repetition, exaggerated confidence, or unsupported achievements.
    """

    job_title: str = dspy.InputField(desc="Target job title")
    company: str = dspy.InputField(desc="Company name for salutation and context")
    job_description: str = dspy.InputField(desc="Pruned job excerpt with the most relevant requirements and responsibilities")
    cv_summary: str = dspy.InputField(desc="Short CV summary with the candidate's highest-level positioning")
    cv_text: str = dspy.InputField(desc="Pruned CV evidence excerpt with relevant skills, experience, and achievements")
    response_language: str = dspy.InputField(desc="Language for the final cover letter")
    cover_letter: str = dspy.OutputField(
        desc="Plain text only. Include greeting, 2-3 short paragraphs, and sign-off. Keep it specific to the role, concise, professional, and roughly under 180 words."
    )


class CoverLetterModule(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(CoverLetterSignature)

    def forward(
        self,
        job_title: str,
        company: str,
        job_description: str,
        cv_summary: str,
        cv_text: str,
        response_language: str,
        max_tokens: int | None = None,
    ):
        if max_tokens is None:
            return self.predict(
                job_title=job_title,
                company=company,
                job_description=job_description,
                cv_summary=cv_summary,
                cv_text=cv_text,
                response_language=response_language,
            )

        with dspy_lm_override(max_tokens=max_tokens):
            return self.predict(
                job_title=job_title,
                company=company,
                job_description=job_description,
                cv_summary=cv_summary,
                cv_text=cv_text,
                response_language=response_language,
            )


class CoverLetterService:
    def __init__(self) -> None:
        settings = get_settings()
        self.generator: CoverLetterModule | None = None
        self.timeout_seconds = settings.ai_timeout_seconds
        self.max_tokens = getattr(settings, "cover_letter_max_tokens", DEFAULT_COVER_LETTER_MAX_TOKENS)
        self._executor = ThreadPoolExecutor(max_workers=2)

    def _get_generator(self) -> CoverLetterModule:
        if self.generator is None:
            try:
                configure_dspy()
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI analysis is not configured.",
                ) from exc
            self.generator = CoverLetterModule()
        return self.generator

    def generate_cover_letter(
        self,
        session: Session,
        user: User,
        job_id: int,
        selected_cv_id: int,
        language: AIResponseLanguage = "english",
        regenerate: bool = False,
    ) -> str:
        selected_language = normalize_language(language)
        job = crud.get_job_for_user(session, user.id, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")

        cv = crud.get_cv_for_user(session, user.id, selected_cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")

        if not regenerate:
            cached_cover_letter = crud.get_cached_cover_letter(
                session=session,
                user_id=user.id,
                job_id=job_id,
                cv_id=selected_cv_id,
                language=selected_language,
            )
            if cached_cover_letter:
                logger.info(
                    "ai_cache operation=cover_letter_generation cache_status=hit source=db job_id=%s cv_id=%s",
                    job_id,
                    selected_cv_id,
                )
                return cached_cover_letter

        logger.info("ai_cache operation=cover_letter_generation cache_status=miss source=none")
        job_excerpt = build_job_excerpt(job.clean_description)
        cv_summary = getattr(cv, "library_summary", "") or cv.summary
        cv_excerpt = build_cv_excerpt(
            cv.clean_text,
            summary=cv.summary,
            library_summary=cv_summary,
            job_description=job_excerpt,
        )
        try:
            generator = self._get_generator()
            logger.info(
                "ai_call operation=cover_letter_generation job_id=%s cv_id=%s regenerate=%s",
                job_id,
                selected_cv_id,
                regenerate,
            )
            result = run_ai_call_with_circuit_breaker(
                executor=self._executor,
                timeout_seconds=self.timeout_seconds,
                operation="cover_letter_generation",
                logger=logger,
                callable_=generator,
                lm_max_tokens=self.max_tokens,
                job_title=job.title,
                company=job.company,
                job_description=job_excerpt,
                cv_summary=cv_summary,
                cv_text=cv_excerpt,
                response_language=language_instruction(selected_language),
                max_tokens=self.max_tokens,
            )
            cover_letter = _normalize_cover_letter(result.cover_letter)
        except HTTPException as exc:
            logger.warning(
                "ai_fallback operation=cover_letter_generation fallback=true reason=http_%s",
                exc.status_code,
            )
            cover_letter = self._build_fallback_cover_letter(job=job, cv=cv, language=selected_language)
        except Exception as exc:
            if looks_like_ai_auth_error(exc):
                logger.warning("ai_fallback operation=cover_letter_generation fallback=true reason=auth")
            else:
                logger.warning("ai_fallback operation=cover_letter_generation fallback=true reason=exception", exc_info=exc)
            cover_letter = self._build_fallback_cover_letter(job=job, cv=cv, language=selected_language)
        if not cover_letter:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The generated cover letter was empty. Please try again.",
            )

        crud.update_job_cover_letter(
            session=session,
            job=job,
            cv_id=selected_cv_id,
            language=selected_language,
            cover_letter=cover_letter,
        )
        return cover_letter

    def _build_fallback_cover_letter(self, *, job: object, cv: object, language: AIResponseLanguage) -> str:
        role_keywords = _extract_role_keywords(job.clean_description)
        matching_keywords = [keyword for keyword in role_keywords if keyword.lower() in cv.clean_text.lower()]
        focus_keywords = matching_keywords[:2] or role_keywords[:2] or ["software delivery"]

        if language == "spanish":
            body = (
                f"Estimado equipo de {job.company},\n\n"
                f"Me interesa postularme al puesto de {job.title}. Mi experiencia en {', '.join(focus_keywords)} "
                f"se alinea con el trabajo descrito y con el tipo de impacto que buscan para este rol.\n\n"
                f"He desarrollado proyectos y entregas concretas relacionados con {', '.join(focus_keywords)}, "
                f"y puedo aportar una forma de trabajo clara, colaborativa y orientada a resultados desde el primer dia.\n\n"
                "Gracias por su tiempo y consideracion."
            )
        else:
            body = (
                f"Dear {job.company} team,\n\n"
                f"I am excited to apply for the {job.title} role. My experience with {', '.join(focus_keywords)} "
                f"aligns well with the kind of work described for this position.\n\n"
                f"I have delivered practical work related to {', '.join(focus_keywords)}, and I would bring a clear, "
                f"collaborative, and execution-focused approach from day one.\n\n"
                "Thank you for your time and consideration."
            )

        return _normalize_cover_letter(body)


def _normalize_cover_letter(value: object) -> str:
    if not isinstance(value, str):
        return ""

    text = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""

    paragraphs = [" ".join(block.split()) for block in text.split("\n\n") if block.strip()]
    if not paragraphs:
        text = "\n\n".join(
            part for part in [_normalize_text(text, MAX_COVER_LETTER_CHARS)] if part
        )
    else:
        compact_paragraphs = [
            _normalize_text(paragraph, MAX_COVER_LETTER_PARAGRAPH_CHARS)
            for paragraph in paragraphs[:MAX_COVER_LETTER_PARAGRAPHS]
        ]
        text = "\n\n".join(paragraph for paragraph in compact_paragraphs if paragraph)

    return text[:MAX_COVER_LETTER_CHARS].strip()


_service: CoverLetterService | None = None


def get_cover_letter_service() -> CoverLetterService:
    global _service
    if _service is None:
        _service = CoverLetterService()
    return _service


def _extract_role_keywords(job_description: str) -> list[str]:
    prioritized = ["Python", "FastAPI", "SQL", "PostgreSQL", "Docker", "Testing", "REST APIs", "Backend"]
    lowered = job_description.lower()
    found: list[str] = []

    for keyword in prioritized:
        lookup = keyword.lower().replace("rest apis", "rest api")
        if lookup in lowered and keyword not in found:
            found.append(keyword)

    if found:
        return found[:3]

    generic = [token.title() for token in WORD_RE.findall(job_description) if len(token) > 4]
    deduped: list[str] = []
    for token in generic:
        if token not in deduped:
            deduped.append(token)
    return deduped[:3]
