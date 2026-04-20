import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor

from app.core.runtime import configure_runtime_environment

configure_runtime_environment()

import dspy
from fastapi import HTTPException, status

from app.core.ai import dspy_lm_override, run_ai_call_with_circuit_breaker
from app.core.ai import build_ai_failure_http_exception
from app.core.config import configure_dspy, get_settings
from app.schemas.job import AIResponseLanguage
from app.schemas.cv import CvAnalysisResponse
from app.services.job_analyzer import _normalize_list, _normalize_text
from app.services.job_preprocessing import build_cv_excerpt, build_job_excerpt
from app.services.response_language import language_instruction, normalize_language


MAX_SUMMARY_CHARS = 420
DEFAULT_CV_MATCH_MAX_TOKENS = 1100
CV_MATCH_RETRY_MIN_EXCERPT_CHARS = 900
logger = logging.getLogger(__name__)
WORD_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+#.-]{2,}\b")
NON_SIGNAL_WORDS = {
    "about",
    "across",
    "add",
    "align",
    "application",
    "better",
    "bullet",
    "bullets",
    "candidate",
    "clear",
    "clearly",
    "concrete",
    "cv",
    "evidence",
    "example",
    "examples",
    "exact",
    "focus",
    "highlight",
    "improve",
    "improvements",
    "interview",
    "keyword",
    "keywords",
    "match",
    "move",
    "narrative",
    "next",
    "outcomes",
    "posting",
    "prepare",
    "project",
    "projects",
    "proof",
    "recruiter",
    "relevant",
    "resume",
    "role",
    "section",
    "sections",
    "show",
    "skills",
    "specific",
    "steps",
    "story",
    "strength",
    "summary",
    "tailor",
    "topic",
    "topics",
    "truthful",
    "wording",
}


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
        desc="Max 4 substantive items, ideally 6-16 words each. Only include role-relevant evidence clearly supported by the CV. No advice, no missing items, and no restating the summary."
    )
    missing_skills: list[str] = dspy.OutputField(
        desc="Max 4 substantive items, ideally 6-16 words each, naming the most important missing skills, missing evidence, or unclear proof points. No advice or generic filler."
    )
    likely_fit_level: str = dspy.OutputField(
        desc="Exactly one of: Strong, Moderate, Weak. Be conservative if evidence is thin."
    )
    resume_improvements: list[str] = dspy.OutputField(
        desc="Max 3 concrete CV-edit actions, ideally 6-18 words each. Focus only on changing bullet content, ordering, or proof in the resume itself. Do not repeat ATS, recruiter, interview, or next-step guidance."
    )
    ats_improvements: list[str] = dspy.OutputField(
        desc="Max 3 ATS-focused actions, ideally 6-16 words each, only about keyword wording, exact terminology, skills-section coverage, and alignment to the posting. Do not repeat resume bullets or recruiter advice."
    )
    recruiter_improvements: list[str] = dspy.OutputField(
        desc="Max 3 recruiter-facing actions, ideally 6-16 words each, only about credibility, specificity, business impact, and narrative strength. Do not repeat ATS or resume-edit advice."
    )
    rewritten_bullets: list[str] = dspy.OutputField(
        desc="Max 3 rewritten CV bullet examples tailored to this role. Each bullet should sound resume-ready, include action + context + measurable or concrete outcome, and stay grounded in the provided evidence."
    )
    interview_focus: list[str] = dspy.OutputField(
        desc="Max 3 concrete interview prep topics, ideally 5-16 words each. These are live discussion topics to prepare for, not resume edits or ATS tweaks."
    )
    next_steps: list[str] = dspy.OutputField(
        desc="Max 3 immediate next steps, ideally 6-18 words each, for what the candidate should do next after reading this analysis. Keep them action-oriented and distinct from the resume, ATS, recruiter, and interview lists."
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
            logger.warning("ai_call_http_error operation=cv_match_analysis status_code=%s", exc.status_code)
            raise
        except Exception as exc:
            raise build_ai_failure_http_exception(
                exc=exc,
                logger=logger,
                operation="cv_match_analysis",
                default_detail="Failed to compare the CV against this job. Please try again.",
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
        response = _refine_cv_analysis_response(response)
        if not _is_meaningful_cv_analysis(response):
            logger.warning("ai_invalid_output operation=cv_match_analysis reason=low_quality_output")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "The AI returned a low-quality CV analysis. "
                    "Please try again with the AI provider available."
                ),
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

        text = " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip(" -")
        return _normalize_text(text, MAX_SUMMARY_CHARS)

_cv_service: CvAnalyzerService | None = None


def get_cv_analyzer_service() -> CvAnalyzerService:
    global _cv_service
    if _cv_service is None:
        _cv_service = CvAnalyzerService()
    return _cv_service
def _is_meaningful_cv_analysis(response: CvAnalysisResponse) -> bool:
    if not response.fit_summary.strip():
        return False
    populated_lists = sum(
        1
        for items in (
            response.strengths,
            response.missing_skills,
            response.resume_improvements,
            response.interview_focus,
            response.next_steps,
        )
        if items
    )
    return populated_lists >= 3


def looks_like_fallback_cv_analysis(response: CvAnalysisResponse) -> bool:
    summary = response.fit_summary.lower().strip()
    if summary.startswith("the cv aligns best with ") or summary.startswith("el cv muestra alineacion con "):
        return True
    if summary == "the cv needs clearer evidence to show fit for this role.":
        return True
    if summary == "el cv necesita mas evidencia concreta para demostrar encaje con este puesto.":
        return True

    formulaic_patterns = (
        "demonstrated experience with",
        "clear evidence of",
        "add measurable examples that show",
        "use the job's wording for",
        "prepare specific examples about",
        "falta evidencia clara de",
        "agrega logros o proyectos que demuestren",
    )
    items = [
        *response.strengths,
        *response.missing_skills,
        *response.resume_improvements,
        *response.ats_improvements,
        *response.interview_focus,
    ]
    hits = sum(
        any(item.lower().strip().startswith(pattern) for pattern in formulaic_patterns)
        for item in items
    )
    return hits >= 3


def _refine_cv_analysis_response(response: CvAnalysisResponse) -> CvAnalysisResponse:
    strengths = _dedupe_items(response.strengths, limit=4)
    missing_skills = _dedupe_items(response.missing_skills, limit=4, blocked_items=strengths)
    rewritten_bullets = _dedupe_items(response.rewritten_bullets, limit=2)
    resume_improvements = _dedupe_items(
        response.resume_improvements,
        limit=3,
        blocked_items=strengths + rewritten_bullets,
    )
    ats_improvements = _dedupe_items(
        response.ats_improvements,
        limit=3,
        blocked_items=resume_improvements + rewritten_bullets,
    )
    recruiter_improvements = _dedupe_items(
        response.recruiter_improvements,
        limit=3,
        blocked_items=resume_improvements + ats_improvements + rewritten_bullets,
    )
    interview_focus = _dedupe_items(
        response.interview_focus,
        limit=3,
        blocked_items=resume_improvements + ats_improvements + recruiter_improvements,
    )
    next_steps = _dedupe_items(
        response.next_steps,
        limit=3,
        blocked_items=resume_improvements + ats_improvements + recruiter_improvements + interview_focus,
    )
    return response.model_copy(
        update={
            "strengths": strengths,
            "missing_skills": missing_skills,
            "rewritten_bullets": rewritten_bullets,
            "resume_improvements": resume_improvements,
            "ats_improvements": ats_improvements,
            "recruiter_improvements": recruiter_improvements,
            "interview_focus": interview_focus,
            "next_steps": next_steps,
        }
    )


def _dedupe_items(
    items: list[str],
    *,
    limit: int,
    blocked_items: list[str] | None = None,
) -> list[str]:
    blocked_signatures = [_item_signature(item) for item in blocked_items or [] if item.strip()]
    kept: list[str] = []
    kept_signatures: list[set[str]] = []
    for item in items:
        normalized = _normalize_text(item, 180).strip()
        if not normalized:
            continue
        signature = _item_signature(normalized)
        if signature:
            if any(_signatures_overlap(signature, blocked) for blocked in blocked_signatures):
                continue
            if any(_signatures_overlap(signature, existing) for existing in kept_signatures):
                continue
            kept_signatures.append(signature)
        elif normalized in kept:
            continue
        kept.append(normalized)
        if len(kept) >= limit:
            break
    return kept


def _item_signature(value: str) -> set[str]:
    tokens = {
        token.lower()
        for token in WORD_RE.findall(value)
        if token.lower() not in NON_SIGNAL_WORDS and len(token) >= 4
    }
    return tokens


def _signatures_overlap(left: set[str], right: set[str]) -> bool:
    if not left or not right:
        return False
    overlap = left & right
    return len(overlap) >= 2 or overlap == left or overlap == right
