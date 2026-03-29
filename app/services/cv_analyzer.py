import logging
import time

import dspy
from fastapi import HTTPException, status

from app.core.config import configure_dspy
from app.schemas.job import AIResponseLanguage
from app.schemas.cv import CvAnalysisResponse
from app.services.job_analyzer import _normalize_list, _normalize_text
from app.services.response_language import language_instruction, normalize_language


MAX_LIST_ITEMS = 4
MAX_ITEM_CHARS = 60
logger = logging.getLogger(__name__)


class CvFitSignature(dspy.Signature):
    """Return short CV-job fit insights."""

    title: str = dspy.InputField(desc="Job title")
    job: str = dspy.InputField(desc="Key job text")
    cv: str = dspy.InputField(desc="Key CV text")
    response_language: str = dspy.InputField(desc="Language instruction for all generated content")

    fit_summary: str = dspy.OutputField(desc="A complete 2-4 sentence summary without truncation")
    strengths: list[str] = dspy.OutputField(desc="Up to 4 strengths")
    missing_skills: list[str] = dspy.OutputField(desc="Up to 4 gaps")
    likely_fit_level: str = dspy.OutputField(desc="Strong, Moderate, or Weak")
    resume_improvements: list[str] = dspy.OutputField(desc="Up to 4 resume fixes")
    interview_focus: list[str] = dspy.OutputField(desc="Up to 4 interview topics")
    next_steps: list[str] = dspy.OutputField(desc="Up to 4 next steps")


class CvFitModule(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(CvFitSignature)

    def forward(self, job_title: str, job_description: str, cv_text: str, response_language: str):
        return self.predict(
            title=job_title,
            job=job_description,
            cv=cv_text,
            response_language=response_language,
        )


class CvAnalyzerService:
    def __init__(self) -> None:
        self.analyzer: CvFitModule | None = None

    def _get_analyzer(self) -> CvFitModule:
        if self.analyzer is None:
            try:
                configure_dspy()
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="AI analysis is not configured.",
                ) from exc
            self.analyzer = CvFitModule()
        return self.analyzer

    def analyze(
        self,
        job_title: str,
        job_description: str,
        cv_text: str,
        language: AIResponseLanguage = "english",
    ) -> CvAnalysisResponse:
        selected_language = normalize_language(language)
        dspy_start = time.perf_counter()
        try:
            result = self._get_analyzer()(
                job_title=job_title,
                job_description=job_description,
                cv_text=cv_text,
                response_language=language_instruction(selected_language),
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to analyze CV. Please try again.",
            ) from exc
        finally:
            logger.info(
                "cv_fit dspy_call_ms=%.1f",
                (time.perf_counter() - dspy_start) * 1000,
            )

        mapping_start = time.perf_counter()
        response = CvAnalysisResponse(
            fit_summary=self._normalize_summary(result.fit_summary),
            strengths=_normalize_list(result.strengths),
            missing_skills=_normalize_list(result.missing_skills),
            likely_fit_level=_normalize_text(result.likely_fit_level, 20),
            resume_improvements=_normalize_list(result.resume_improvements),
            interview_focus=_normalize_list(result.interview_focus),
            next_steps=_normalize_list(result.next_steps),
        )
        logger.info(
            "cv_fit response_map_ms=%.1f",
            (time.perf_counter() - mapping_start) * 1000,
        )
        return response

    @staticmethod
    def _normalize_summary(value: object) -> str:
        if not isinstance(value, str):
            return ""

        # Preserve full AI summary while cleaning whitespace/newlines.
        return " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip(" -")




_cv_service: CvAnalyzerService | None = None


def get_cv_analyzer_service() -> CvAnalyzerService:
    global _cv_service
    if _cv_service is None:
        _cv_service = CvAnalyzerService()
    return _cv_service
