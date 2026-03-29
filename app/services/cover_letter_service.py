from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

import dspy
from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.config import configure_dspy, get_settings
from app.db import crud
from app.models import User
from app.schemas.job import AIResponseLanguage
from app.services.job_analyzer import _normalize_text
from app.services.response_language import language_instruction, normalize_language


MAX_COVER_LETTER_CHARS = 2400


class CoverLetterSignature(dspy.Signature):
    """Generate a short plain-text cover letter for one job using one CV."""

    job_title: str = dspy.InputField(desc="Job title")
    company: str = dspy.InputField(desc="Company name")
    job_description: str = dspy.InputField(desc="Clean job description")
    cv_summary: str = dspy.InputField(desc="Short CV summary")
    cv_text: str = dspy.InputField(desc="Clean CV text")
    response_language: str = dspy.InputField(desc="Language instruction for all generated content")
    cover_letter: str = dspy.OutputField(
        desc="Plain text cover letter with greeting, 2-3 short paragraphs, and sign-off"
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
    ):
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
        configure_dspy()
        settings = get_settings()
        self.generator = CoverLetterModule()
        self.timeout_seconds = settings.dspy_timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=2)

    def generate_cover_letter(
        self,
        session: Session,
        user: User,
        job_id: int,
        selected_cv_id: int,
        language: AIResponseLanguage = "english",
    ) -> str:
        selected_language = normalize_language(language)
        job = crud.get_job_for_user(session, user.id, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")

        cv = crud.get_cv_for_user(session, user.id, selected_cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")

        try:
            future = self._executor.submit(
                self.generator,
                job_title=job.title,
                company=job.company,
                job_description=job.clean_description,
                cv_summary=cv.summary,
                cv_text=cv.clean_text,
                response_language=language_instruction(selected_language),
            )
            result = future.result(timeout=self.timeout_seconds)
        except FuturesTimeoutError as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Cover letter generation timed out. Please retry.",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to generate cover letter. Please try again.",
            ) from exc

        cover_letter = _normalize_cover_letter(result.cover_letter)
        if not cover_letter:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The generated cover letter was empty. Please try again.",
            )

        return cover_letter


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
        text = "\n\n".join(paragraph[:MAX_COVER_LETTER_CHARS].rstrip() for paragraph in paragraphs)

    return text[:MAX_COVER_LETTER_CHARS].strip()


_service: CoverLetterService | None = None


def get_cover_letter_service() -> CoverLetterService:
    global _service
    if _service is None:
        _service = CoverLetterService()
    return _service
