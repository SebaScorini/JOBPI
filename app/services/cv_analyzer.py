import logging
import time
from concurrent.futures import ThreadPoolExecutor
import re

from app.core.runtime import configure_runtime_environment

configure_runtime_environment()

import dspy
from fastapi import HTTPException, status

from app.core.ai import dspy_lm_override, looks_like_ai_auth_error, run_ai_call_with_circuit_breaker
from app.core.config import configure_dspy, get_settings
from app.schemas.job import AIResponseLanguage
from app.schemas.cv import CvAnalysisResponse
from app.services.job_analyzer import _normalize_list, _normalize_text
from app.services.job_preprocessing import build_cv_excerpt, build_job_excerpt
from app.services.response_language import language_instruction, normalize_language


MAX_LIST_ITEMS = 5
MAX_ITEM_CHARS = 140
MAX_SUMMARY_CHARS = 420
DEFAULT_CV_MATCH_MAX_TOKENS = 1100
CV_MATCH_RETRY_MIN_EXCERPT_CHARS = 900
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
    """Compare CV evidence against job requirements and return high-signal fit guidance.

    Use only information supported by the provided CV excerpt and job excerpt. Prefer explicit
    matches, specific missing evidence, and concrete improvements over generic career advice.
    Do not invent experience, inflate fit, or mention irrelevant technologies. Be direct, specific,
    and useful enough that the candidate can act on the analysis immediately.
    """

    title: str = dspy.InputField(desc="Job title for role framing")
    job: str = dspy.InputField(desc="Pruned job excerpt emphasizing requirements, responsibilities, and tools")
    cv: str = dspy.InputField(desc="Pruned CV excerpt emphasizing summary, skills, recent experience, and metrics")
    response_language: str = dspy.InputField(desc="Language for every output field")

    fit_summary: str = dspy.OutputField(
        desc="2-3 concrete sentences on overall fit, strongest evidence from the CV, biggest gap, and what that means for candidacy. Stay grounded in the provided text."
    )
    strengths: list[str] = dspy.OutputField(
        desc="Max 5 substantive items, ideally 6-16 words each, with only role-relevant strengths clearly supported by the CV."
    )
    missing_skills: list[str] = dspy.OutputField(
        desc="Max 5 substantive items, ideally 6-16 words each, naming the most important missing skills, missing evidence, or unclear proof points."
    )
    likely_fit_level: str = dspy.OutputField(
        desc="Exactly one of: Strong, Moderate, Weak. Be conservative if evidence is thin."
    )
    resume_improvements: list[str] = dspy.OutputField(
        desc="Max 5 concrete action items, ideally 6-18 words each, for CV edits that would show fit better."
    )
    ats_improvements: list[str] = dspy.OutputField(
        desc="Max 4 concrete ATS-focused actions, ideally 6-16 words each, about exact wording, keyword placement, skills sections, and alignment to the posting."
    )
    recruiter_improvements: list[str] = dspy.OutputField(
        desc="Max 4 recruiter-focused actions, ideally 6-16 words each, about impact, credibility, specificity, and narrative strength."
    )
    rewritten_bullets: list[str] = dspy.OutputField(
        desc="Max 3 rewritten CV bullet examples tailored to this role. Each bullet should sound resume-ready, include action + context + measurable or concrete outcome, and stay grounded in the provided evidence."
    )
    interview_focus: list[str] = dspy.OutputField(
        desc="Max 5 concrete prep topics, ideally 5-16 words each, based on the strongest match areas or biggest gaps."
    )
    next_steps: list[str] = dspy.OutputField(
        desc="Max 5 immediate next steps, ideally 6-18 words each, to improve this exact application."
    )


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
        self.max_tokens = getattr(settings, "cv_match_max_tokens", DEFAULT_CV_MATCH_MAX_TOKENS)
        self.retry_max_tokens = getattr(settings, "cv_match_retry_max_tokens", self.max_tokens)
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
        job_excerpt = build_job_excerpt(job_description)
        cv_excerpt = build_cv_excerpt(cv_text, job_description=job_excerpt)
        retry_job_excerpt = build_job_excerpt(
            job_description,
            max_chars=min(
                len(job_excerpt),
                max(CV_MATCH_RETRY_MIN_EXCERPT_CHARS, int(len(job_excerpt) * 0.75)),
            ),
        )
        retry_cv_excerpt = build_cv_excerpt(
            cv_text,
            job_description=retry_job_excerpt,
            max_chars=min(
                len(cv_excerpt),
                max(CV_MATCH_RETRY_MIN_EXCERPT_CHARS, int(len(cv_excerpt) * 0.75)),
            ),
        )
        dspy_start = time.perf_counter()
        try:
            result = run_ai_call_with_circuit_breaker(
                executor=self._executor,
                timeout_seconds=self.timeout_seconds,
                operation="cv_match_analysis",
                logger=logger,
                callable_=self._get_analyzer(),
                lm_max_tokens=self.max_tokens,
                retry_lm_max_tokens=self.retry_max_tokens,
                attempt_kwargs_builder=lambda attempt: {
                    "job_title": job_title,
                    "job_description": job_excerpt if attempt == 0 else retry_job_excerpt,
                    "cv_text": cv_excerpt if attempt == 0 else retry_cv_excerpt,
                    "response_language": language_instruction(selected_language),
                    "max_tokens": self.max_tokens if attempt == 0 else self.retry_max_tokens,
                },
            )
        except HTTPException as exc:
            logger.warning(
                "ai_fallback operation=cv_match_analysis fallback=true reason=http_%s",
                exc.status_code,
            )
            return self._build_fallback_analysis(
                job_title=job_title,
                job_description=job_description,
                cv_text=cv_text,
                language=selected_language,
            )
        except Exception as exc:
            if looks_like_ai_auth_error(exc):
                logger.warning("ai_fallback operation=cv_match_analysis fallback=true reason=auth")
            else:
                logger.warning("ai_fallback operation=cv_match_analysis fallback=true reason=exception", exc_info=exc)
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
            ats_improvements=_normalize_list(getattr(result, "ats_improvements", [])),
            recruiter_improvements=_normalize_list(getattr(result, "recruiter_improvements", [])),
            rewritten_bullets=_normalize_list(getattr(result, "rewritten_bullets", [])),
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
            ats_improvements = [f"Incluye {item} con el wording del aviso cuando sea veraz" for item in missing[:MAX_LIST_ITEMS]]
            recruiter_improvements = [f"Cuantifica tu impacto relacionado con {item}" for item in matched[:MAX_LIST_ITEMS] or missing[:MAX_LIST_ITEMS]]
            rewritten_bullets = [f"Demostre {item} en un proyecto o experiencia reciente con contexto e impacto medible" for item in matched[:3]]
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
            ats_improvements = [f"Use the job's wording for {item} where it is truthful" for item in missing[:MAX_LIST_ITEMS]]
            recruiter_improvements = [f"Quantify your impact around {item}" for item in matched[:MAX_LIST_ITEMS] or missing[:MAX_LIST_ITEMS]]
            rewritten_bullets = [f"Demonstrated {item} in a recent project or role with concrete scope and measurable impact" for item in matched[:3]]
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
            ats_improvements=_normalize_list(ats_improvements),
            recruiter_improvements=_normalize_list(recruiter_improvements),
            rewritten_bullets=_normalize_list(rewritten_bullets),
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
