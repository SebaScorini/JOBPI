import logging
import time

import dspy
from fastapi import HTTPException, status

from app.core.config import configure_dspy
from app.schemas.cv import CvAnalysisResponse
from app.services.job_analyzer import _normalize_list, _normalize_text


MAX_LIST_ITEMS = 4
MAX_ITEM_CHARS = 60
MAX_SUMMARY_CHARS = 180
logger = logging.getLogger(__name__)


class CvFitSignature(dspy.Signature):
    """Return short CV-job fit insights."""

    title: str = dspy.InputField(desc="Job title")
    job: str = dspy.InputField(desc="Key job text")
    cv: str = dspy.InputField(desc="Key CV text")

    fit_summary: str = dspy.OutputField(desc="One short summary")
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

    def forward(self, job_title: str, job_description: str, cv_text: str):
        return self.predict(
            title=job_title,
            job=job_description,
            cv=cv_text,
        )


class CvAnalyzerService:
    def __init__(self) -> None:
        configure_dspy()
        self.analyzer = CvFitModule()

    def analyze(
        self,
        job_title: str,
        job_description: str,
        cv_text: str,
    ) -> CvAnalysisResponse:
        dspy_start = time.perf_counter()
        try:
            result = self.analyzer(
                job_title=job_title,
                job_description=job_description,
                cv_text=cv_text,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to analyze CV: {exc}",
            ) from exc
        finally:
            logger.info(
                "cv_fit dspy_call_ms=%.1f",
                (time.perf_counter() - dspy_start) * 1000,
            )

        mapping_start = time.perf_counter()
        response = CvAnalysisResponse(
            fit_summary=_normalize_text(result.fit_summary, MAX_SUMMARY_CHARS),
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




_cv_service: CvAnalyzerService | None = None


def get_cv_analyzer_service() -> CvAnalyzerService:
    global _cv_service
    if _cv_service is None:
        _cv_service = CvAnalyzerService()
    return _cv_service
