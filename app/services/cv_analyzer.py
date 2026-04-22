import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor

from app.core.runtime import configure_runtime_environment

configure_runtime_environment()

import dspy
from fastapi import HTTPException, status

from app.core.ai import build_ai_failure_http_exception
from app.core.ai import dspy_lm_override, run_structured_ai_call, use_provider_fallback_model
from app.core.config import configure_dspy, get_settings
from app.models.ai_schemas import CvAnalysisAIOutput
from app.schemas.job import AIResponseLanguage
from app.schemas.cv import CvAnalysisResponse
from app.services.job_analyzer import _normalize_list, _normalize_text
from app.services.job_preprocessing import build_cv_context, build_job_context, clean_description
from app.services.pdf_extractor import preprocess_cv_text
from app.services.response_language import language_instruction, normalize_language


MAX_SUMMARY_CHARS = 700
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
MISSING_SKILL_ACTION_PREFIXES = (
    "add ",
    "show ",
    "highlight ",
    "use ",
    "move ",
    "quantify ",
    "prepare ",
    "rewrite ",
    "include ",
    "update ",
)
GENERIC_MISSING_SKILL_PHRASES = (
    "more experience",
    "additional experience",
    "better alignment",
    "stronger alignment",
    "broader background",
    "more background",
    "more exposure",
    "stronger experience",
    "relevant experience",
    "general experience",
)


class CvFitSignature(dspy.Signature):
    """Compare CV evidence against job requirements and return high-signal fit guidance.

    Use only information supported by the provided CV excerpt and job excerpt. Prefer explicit
    matches, specific missing evidence, and concrete improvements over generic career advice.
    Do not invent experience, inflate fit, or mention irrelevant technologies. Be direct, specific,
    and useful enough that the candidate can act on the analysis immediately.
    Do not use generic buzzwords, empty praise, unsupported claims, or assume the role is technical
    if the posting is not. Do not repeat the prompt, do not summarize the CV broadly, and do not
    collapse different recommendation types into similar filler.
    Keep the recommendation lists clearly separated: resume_improvements are CV edits, ats_improvements
    are wording and keyword alignment, recruiter_improvements are credibility and impact framing,
    interview_focus are discussion topics, and next_steps are immediate actions after reading the analysis.
    Avoid reusing the same phrase stem across multiple lists.
    Prioritize filling these sections completely, in this order, if output budget gets tight:
    rewritten_bullets, resume_improvements, ats_improvements, recruiter_improvements, strengths,
    missing_skills. Interview focus and next steps are lowest priority.
    """

    title: str = dspy.InputField(desc="Job title for role framing")
    job: str = dspy.InputField(desc="Cleaned, high-signal job description emphasizing requirements, responsibilities, and tools")
    cv: str = dspy.InputField(desc="Cleaned CV text emphasizing summary, skills, recent experience, and measurable evidence")
    response_language: str = dspy.InputField(desc="Language for every output field")

    fit_summary: str = dspy.OutputField(
        desc="Exactly 2 concise sentences, ideally 45-80 words total, on overall fit, strongest CV evidence, biggest gap, and what that means for candidacy. Mention at least one specific capability, project type, or outcome evidenced in the CV when possible. Do not consume the budget with a long narrative."
    )
    likely_fit_level: str = dspy.OutputField(
        desc="Exactly one of: Strong, Moderate, Weak. Be conservative if evidence is thin."
    )
    rewritten_bullets: list[str] = dspy.OutputField(
        desc="Max 3 rewritten CV bullet examples tailored to this role. Each bullet should sound resume-ready, include action + context + measurable or concrete outcome, and stay grounded in the provided evidence."
    )
    resume_improvements: list[str] = dspy.OutputField(
        desc="Max 3 concrete CV-edit actions, ideally 5-12 words each. Focus only on changing bullet content, ordering, or proof in the resume itself. Name what evidence or bullet should change, and do not repeat ATS, recruiter, interview, or next-step guidance."
    )
    ats_improvements: list[str] = dspy.OutputField(
        desc="Max 3 ATS-focused actions, ideally 5-12 words each, only about keyword wording, exact terminology, skills-section coverage, and alignment to the posting. Prefer exact posting language when possible and do not repeat resume bullets or recruiter advice."
    )
    recruiter_improvements: list[str] = dspy.OutputField(
        desc="Max 3 recruiter-facing actions, ideally 5-12 words each, only about credibility, specificity, business impact, and narrative strength. Push for stronger proof and business framing, and do not repeat ATS or resume-edit advice."
    )
    strengths: list[str] = dspy.OutputField(
        desc="Max 4 substantive items, ideally 5-12 words each. Only include role-relevant evidence clearly supported by the CV. No advice, no missing items, and no restating the summary."
    )
    missing_skills: list[str] = dspy.OutputField(
        desc="Max 4 substantive items, ideally 5-12 words each, naming the most important missing skill, missing responsibility, or missing proof point. Each item must name a concrete technology, responsibility, domain, or evidence gap from the role. This section is diagnosis only: no advice, no action verbs, no generic filler like 'more experience', and no overlap with resume or ATS improvements."
    )
    interview_focus: list[str] = dspy.OutputField(
        desc="Max 2 concrete interview prep topics, ideally 4-8 words each. These are live discussion topics to prepare for, not resume edits or ATS tweaks."
    )
    next_steps: list[str] = dspy.OutputField(
        desc="Max 2 immediate next steps, ideally 5-10 words each, for what the candidate should do next after reading this analysis. Keep them action-oriented, sequenced for near-term execution, and distinct from the resume, ATS, recruiter, and interview lists."
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
        model: str | None = None,
    ):
        if max_tokens is None:
            return self.predict(
                title=job_title,
                job=job_description,
                cv=cv_text,
                response_language=response_language,
            )

        with dspy_lm_override(max_tokens=max_tokens, model=model):
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
        cv_summary: str | None = None,
        cv_library_summary: str | None = None,
    ) -> CvAnalysisResponse:
        selected_language = normalize_language(language)
        job_context = build_job_context(clean_description(job_description), title=job_title)
        cv_context = build_cv_context(
            preprocess_cv_text(cv_text),
            summary=cv_summary,
            library_summary=cv_library_summary,
        )
        dspy_start = time.perf_counter()
        try:
            parsed = run_structured_ai_call(
                schema=CvAnalysisAIOutput,
                executor=self._executor,
                timeout_seconds=self.timeout_seconds,
                operation="cv_match_analysis",
                logger=logger,
                callable_=self._get_analyzer(),
                lm_max_tokens=self.max_tokens,
                retry_lm_max_tokens=self.retry_max_tokens,
                attempt_kwargs_builder_with_exception=lambda attempt, previous_exception: {
                    "job_title": job_title,
                    "job_description": job_context,
                    "cv_text": cv_context,
                    "response_language": language_instruction(selected_language),
                    "max_tokens": self.max_tokens if attempt == 0 else self.retry_max_tokens,
                    "model": use_provider_fallback_model(attempt, previous_exception),
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
        result = parsed.payload
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
    # Require a non-trivial fit summary — a placeholder is not enough.
    if len(response.fit_summary.strip()) < 15:
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
    strengths = _dedupe_items(response.strengths, limit=5)
    rewritten_bullets = _dedupe_items(response.rewritten_bullets, limit=4)
    resume_improvements = _dedupe_items(
        response.resume_improvements,
        limit=4,
        blocked_items=strengths + rewritten_bullets,
    )
    ats_improvements = _dedupe_items(
        response.ats_improvements,
        limit=4,
        blocked_items=resume_improvements + rewritten_bullets,
    )
    recruiter_improvements = _dedupe_items(
        response.recruiter_improvements,
        limit=4,
        blocked_items=resume_improvements + ats_improvements + rewritten_bullets,
    )
    interview_focus = _dedupe_items(
        response.interview_focus,
        limit=4,
        blocked_items=resume_improvements + ats_improvements + recruiter_improvements,
    )
    next_steps = _dedupe_items(
        response.next_steps,
        limit=4,
        blocked_items=resume_improvements + ats_improvements + recruiter_improvements + interview_focus,
    )
    missing_skills = _dedupe_items(
        _filter_missing_skill_items(response.missing_skills),
        limit=5,
        blocked_items=(
            strengths
            + rewritten_bullets
            + resume_improvements
            + ats_improvements
            + recruiter_improvements
            + interview_focus
            + next_steps
        ),
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


def _filter_missing_skill_items(items: list[str]) -> list[str]:
    filtered: list[str] = []
    for item in items:
        normalized = _normalize_text(item, 180).strip()
        if not normalized:
            continue

        lowered = normalized.lower()
        if lowered.startswith(MISSING_SKILL_ACTION_PREFIXES):
            continue

        signal_words = [
            token.lower()
            for token in WORD_RE.findall(normalized)
            if token.lower() not in NON_SIGNAL_WORDS
        ]
        if not signal_words:
            continue
        if (
            lowered in GENERIC_MISSING_SKILL_PHRASES
            or (
                len(signal_words) < 3
                and any(lowered.startswith(phrase) for phrase in GENERIC_MISSING_SKILL_PHRASES)
            )
        ):
            continue

        filtered.append(normalized)
    return filtered


def _dedupe_items(
    items: list[str],
    *,
    limit: int,
    blocked_items: list[str] | None = None,
) -> list[str]:
    blocked_values = {
        _normalize_text(item, 180).strip().lower()
        for item in blocked_items or []
        if item.strip()
    }
    kept: list[str] = []
    for item in items:
        normalized = _normalize_text(item, 180).strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in blocked_values or lowered in {entry.lower() for entry in kept}:
            continue
        kept.append(normalized)
        if len(kept) >= limit:
            break
    return kept
