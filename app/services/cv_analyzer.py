import logging
import time
from concurrent.futures import ThreadPoolExecutor
import re

import dspy
from fastapi import HTTPException, status

from app.core.ai import dspy_lm_override, run_ai_call_with_timeout
from app.core.config import configure_dspy, get_settings
from app.schemas.job import AIResponseLanguage
from app.schemas.cv import CvAnalysisResponse
from app.services.job_analyzer import _normalize_list, _normalize_text
from app.services.response_language import language_instruction, normalize_language


MAX_LIST_ITEMS = 4
MAX_ITEM_CHARS = 60
MAX_SUMMARY_CHARS = 280
MATCH_EXPLANATION_MAX_TOKENS = 3000
logger = logging.getLogger(__name__)
WORD_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+#.-]{1,}\b")
MATCH_KEYWORDS: list[tuple[str, str]] = [
    ("python", "Python"),
    ("fastapi", "FastAPI"),
    ("sql", "SQL"),
    ("postgresql", "PostgreSQL"),
    ("postgres", "PostgreSQL"),
    ("docker", "Docker"),
    ("testing", "Testing"),
    ("test", "Testing"),
    ("rest api", "REST APIs"),
    ("apis", "APIs"),
    ("backend", "Backend"),
    ("react", "React"),
    ("typescript", "TypeScript"),
    ("analytics", "Analytics"),
]


class CvFitSignature(dspy.Signature):
    """Return concise CV-vs-job fit insights only.

    Include only actionable, role-specific content.
    Exclude filler, generic advice, repeated ideas, and irrelevant technologies.
    """

    title: str = dspy.InputField(desc="Job title")
    job: str = dspy.InputField(desc="Key job text")
    cv: str = dspy.InputField(desc="Key CV text")
    response_language: str = dspy.InputField(desc="Output language")

    fit_summary: str = dspy.OutputField(desc="1-2 short fit sentences. No fluff or generic claims.")
    strengths: list[str] = dspy.OutputField(desc="Max 4 concrete strengths relevant to this job.")
    missing_skills: list[str] = dspy.OutputField(desc="Max 4 concrete gaps that reduce fit.")
    likely_fit_level: str = dspy.OutputField(desc="Strong, Moderate, or Weak")
    resume_improvements: list[str] = dspy.OutputField(desc="Max 4 targeted CV fixes for this job.")
    interview_focus: list[str] = dspy.OutputField(desc="Max 4 interview focus points for this role.")
    next_steps: list[str] = dspy.OutputField(desc="Max 4 direct next steps. Actionable only.")


class CvFitModule(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(CvFitSignature)

    def forward(
        self,
        job_title: str,
        job_description: str,
        cv_text: str,
        response_language: str,
        max_tokens: int | None = None,
    ):
        if max_tokens is None:
            return self.predict(
                title=job_title,
                job=job_description,
                cv=cv_text,
                response_language=response_language,
            )

        with dspy_lm_override(max_tokens=max_tokens):
            return self.predict(
                title=job_title,
                job=job_description,
                cv=cv_text,
                response_language=response_language,
            )


class CvAnalyzerService:
    def __init__(self) -> None:
        settings = get_settings()
        self.analyzer: CvFitModule | None = None
        self.timeout_seconds = settings.ai_timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=4)

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
            result = run_ai_call_with_timeout(
                executor=self._executor,
                timeout_seconds=self.timeout_seconds,
                operation="cv_match_analysis",
                logger=logger,
                callable_=self._get_analyzer(),
                lm_max_tokens=MATCH_EXPLANATION_MAX_TOKENS,
                job_title=job_title,
                job_description=job_description,
                cv_text=cv_text,
                response_language=language_instruction(selected_language),
                max_tokens=MATCH_EXPLANATION_MAX_TOKENS,
            )
        except HTTPException as exc:
            logger.warning(
                "ai_fallback operation=cv_match_analysis reason=http_%s",
                exc.status_code,
            )
            return self._build_fallback_analysis(
                job_title=job_title,
                job_description=job_description,
                cv_text=cv_text,
                language=selected_language,
            )
        except Exception as exc:
            logger.warning("ai_fallback operation=cv_match_analysis reason=exception", exc_info=exc)
            return self._build_fallback_analysis(
                job_title=job_title,
                job_description=job_description,
                cv_text=cv_text,
                language=selected_language,
            )
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

    def _build_fallback_analysis(
        self,
        *,
        job_title: str,
        job_description: str,
        cv_text: str,
        language: AIResponseLanguage,
    ) -> CvAnalysisResponse:
        matched, missing = _extract_match_signals(job_title=job_title, job_description=job_description, cv_text=cv_text)
        match_ratio = len(matched) / max(1, len(matched) + len(missing))

        if match_ratio >= 0.6 and len(matched) >= 2:
            fit_level = "Strong"
        elif matched:
            fit_level = "Moderate"
        else:
            fit_level = "Weak"

        if language == "spanish":
            summary = (
                f"El CV muestra alineacion con {', '.join(matched[:2])}."
                if matched
                else "El CV necesita mas evidencia concreta para demostrar encaje con este puesto."
            )
            strengths = [f"Experiencia demostrada en {item}" for item in matched[:MAX_LIST_ITEMS]]
            gaps = [f"Falta evidencia clara de {item}" for item in missing[:MAX_LIST_ITEMS]]
            resume_improvements = [f"Agrega logros o proyectos que demuestren {item}" for item in missing[:MAX_LIST_ITEMS]]
            interview_focus = [f"Prepara ejemplos concretos sobre {item}" for item in matched[:MAX_LIST_ITEMS] or missing[:MAX_LIST_ITEMS]]
            next_steps = (
                [f"Actualiza el CV para resaltar {item}" for item in missing[:2]]
                or ["Destaca los logros mas relevantes al inicio del CV"]
            )
        else:
            summary = (
                f"The CV aligns best with {', '.join(matched[:2])}."
                if matched
                else "The CV needs clearer evidence to show fit for this role."
            )
            strengths = [f"Demonstrated experience with {item}" for item in matched[:MAX_LIST_ITEMS]]
            gaps = [f"Clear evidence of {item} is missing" for item in missing[:MAX_LIST_ITEMS]]
            resume_improvements = [f"Add measurable examples that show {item}" for item in missing[:MAX_LIST_ITEMS]]
            interview_focus = [f"Prepare specific examples about {item}" for item in matched[:MAX_LIST_ITEMS] or missing[:MAX_LIST_ITEMS]]
            next_steps = (
                [f"Update the CV to foreground {item}" for item in missing[:2]]
                or ["Move the strongest role-relevant achievements closer to the top of the CV"]
            )

        if not strengths:
            strengths = (
                ["Relevant backend delivery experience", "Transferable product and execution experience"]
                if language == "english"
                else ["Experiencia transferible en entrega de producto", "Base tecnica aplicable al puesto"]
            )

        return CvAnalysisResponse(
            fit_summary=self._normalize_summary(summary),
            strengths=_normalize_list(strengths),
            missing_skills=_normalize_list(gaps),
            likely_fit_level=fit_level,
            resume_improvements=_normalize_list(resume_improvements),
            interview_focus=_normalize_list(interview_focus),
            next_steps=_normalize_list(next_steps),
        )

    @staticmethod
    def _normalize_summary(value: object) -> str:
        if not isinstance(value, str):
            return ""

        text = " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip(" -")
        return _normalize_text(text, MAX_SUMMARY_CHARS)




_cv_service: CvAnalyzerService | None = None


def get_cv_analyzer_service() -> CvAnalyzerService:
    global _cv_service
    if _cv_service is None:
        _cv_service = CvAnalyzerService()
    return _cv_service


def _extract_match_signals(*, job_title: str, job_description: str, cv_text: str) -> tuple[list[str], list[str]]:
    lowered_job = f"{job_title} {job_description}".lower()
    cv_tokens = set(token.lower() for token in WORD_RE.findall(cv_text))
    matched: list[str] = []
    missing: list[str] = []

    for needle, label in MATCH_KEYWORDS:
        if needle not in lowered_job:
            continue
        is_present = all(part in cv_tokens for part in needle.split())
        target = matched if is_present else missing
        if label not in target:
            target.append(label)

    if not matched and cv_tokens:
        job_tokens = [
            token.title()
            for token in WORD_RE.findall(job_title)
            if len(token) > 3 and token.lower() in cv_tokens
        ]
        matched.extend(job_tokens[:2])

    return matched[:MAX_LIST_ITEMS], missing[:MAX_LIST_ITEMS]
