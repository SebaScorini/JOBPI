import re
import logging
from concurrent.futures import ThreadPoolExecutor

from app.core.runtime import configure_runtime_environment

configure_runtime_environment()

import dspy
from fastapi import HTTPException, status

from app.core.ai import (
    build_ai_failure_http_exception,
    dspy_lm_override,
    run_structured_ai_call,
    use_provider_fallback_model,
)
from app.core.config import configure_dspy, get_settings
from app.models.ai_schemas import CvLibrarySummaryAIOutput
from app.services.job_analyzer import _normalize_text
from app.services.job_preprocessing import build_cv_context


# Keep the old symbol name available for tests and local monkeypatching.
run_ai_call_with_timeout = run_structured_ai_call


MAX_LIBRARY_SUMMARY_CHARS = 180
SUMMARY_MAX_TOKENS = 400
logger = logging.getLogger(__name__)
ROLE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Backend-focused profile", re.compile(r"\b(backend|python|fastapi|django|flask|api|microservices?)\b", re.IGNORECASE)),
    ("Full-stack profile", re.compile(r"\b(full[- ]stack|react|node\.?js|typescript|javascript|frontend|backend)\b", re.IGNORECASE)),
    ("Frontend-focused profile", re.compile(r"\b(frontend|react|next\.?js|typescript|javascript|ui|ux)\b", re.IGNORECASE)),
    ("Data-oriented profile", re.compile(r"\b(data|analytics|machine learning|ml|ai|etl|pandas|sql)\b", re.IGNORECASE)),
    ("DevOps-oriented profile", re.compile(r"\b(devops|aws|azure|gcp|docker|kubernetes|terraform|ci/cd)\b", re.IGNORECASE)),
    ("Support-oriented profile", re.compile(r"\b(support|help desk|troubleshooting|customer service|ticketing|it support)\b", re.IGNORECASE)),
]
SENIORITY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Senior", re.compile(r"\b(senior|sr\.?|lead|principal|staff)\b", re.IGNORECASE)),
    ("Mid-level", re.compile(r"\b(mid|semi[- ]?senior|ssr\.?)\b", re.IGNORECASE)),
    ("Junior", re.compile(r"\b(junior|jr\.?|entry[- ]level|trainee|intern)\b", re.IGNORECASE)),
]
TECH_KEYWORDS = [
    "Python",
    "FastAPI",
    "Django",
    "Flask",
    "SQL",
    "PostgreSQL",
    "MySQL",
    "React",
    "TypeScript",
    "JavaScript",
    "Node.js",
    "Docker",
    "Kubernetes",
    "AWS",
    "Azure",
    "GCP",
    "Java",
    "Spring",
    "C#",
    ".NET",
    "PHP",
    "Laravel",
    "Ruby",
    "Rails",
    "Go",
    "REST APIs",
    "GraphQL",
    "Linux",
]


class CvLibrarySummarySignature(dspy.Signature):
    """Generate a compact, high-signal summary for a CV library card.

    Infer only what is clearly supported by the CV excerpt. Prefer role focus, seniority when
    obvious, and the most representative technologies or domains. Avoid filler, fragments,
    buzzwords, and invented claims.
    Do not write generic adjectives, unsupported seniority, or role assumptions that are not
    grounded in the CV. Do not repeat section labels or produce vague "experienced professional"
    summaries. Favor a summary that sounds like a distinct profile snapshot rather than a generic
    resume label.
    """

    cv: str = dspy.InputField(desc="Markdown CV context with summary signals and full useful CV content")
    summary: str = dspy.OutputField(
        desc="1-2 short complete sentences. Mention role focus, seniority only if clear, and 2-4 representative technologies, domains, or outcome areas only when evidenced. Prefer the most distinguishing signals over generic stack lists."
    )


class CvLibrarySummaryModule(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(CvLibrarySummarySignature)

    def forward(self, cv: str, max_tokens: int | None = None, model: str | None = None):
        predict_kwargs = {
            "cv": cv,
            # Keep library summaries isolated per CV upload. Reusing cached LM
            # responses here can surface stale summaries across batch uploads.
            "config": {"cache": False},
        }
        if max_tokens is None:
            return self.predict(**predict_kwargs)

        with dspy_lm_override(max_tokens=max_tokens, model=model):
            return self.predict(**predict_kwargs)


class CvLibrarySummaryService:
    def __init__(self) -> None:
        settings = get_settings()
        self.timeout_seconds = max(10, min(settings.ai_timeout_seconds, 30))
        self._executor = ThreadPoolExecutor(max_workers=2)

    def generate(self, clean_text: str) -> str:
        context = _prepare_cv_context(clean_text)
        if not context:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The CV text is too empty to generate an AI summary.",
            )

        try:
            generator = self._create_generator()
            logger.info("ai_call operation=cv_library_summary")
            parsed = run_ai_call_with_timeout(
                schema=CvLibrarySummaryAIOutput,
                executor=self._executor,
                timeout_seconds=self.timeout_seconds,
                operation="cv_library_summary",
                logger=logger,
                callable_=generator,
                lm_max_tokens=SUMMARY_MAX_TOKENS,
                cv=context,
                max_tokens=SUMMARY_MAX_TOKENS,
                attempt_kwargs_builder_with_exception=lambda attempt, previous_exception: {
                    "cv": context,
                    "max_tokens": SUMMARY_MAX_TOKENS,
                    "model": use_provider_fallback_model(attempt, previous_exception),
                },
            )
            payload = getattr(parsed, "payload", parsed)
            summary = _normalize_library_summary(getattr(payload, "summary", ""))
            if summary:
                return summary
        except HTTPException:
            logger.warning("cv_library_summary_failed reason=http_exception")
            raise
        except Exception as exc:
            raise build_ai_failure_http_exception(
                exc=exc,
                logger=logger,
                operation="cv_library_summary",
                default_detail="Failed to generate CV summary with AI. Please try again.",
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI returned an empty CV summary. Please try again.",
        )

    def _create_generator(self) -> CvLibrarySummaryModule:
        try:
            configure_dspy()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI analysis is not configured.",
            ) from exc
        return CvLibrarySummaryModule()


def _prepare_cv_context(clean_text: str) -> str:
    first_line = next(
        (
            " ".join(line.split()).strip(" -")
            for line in clean_text.splitlines()
            if " ".join(line.split()).strip(" -")
        ),
        "",
    )
    context = build_cv_context(clean_text, summary=first_line or None)
    if first_line:
        return f"{first_line}\n\n{context}"
    return context


def _normalize_library_summary(value: object) -> str:
    if not isinstance(value, str):
        return ""

    text = " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip(" \"'-")
    if not text:
        return ""

    text = re.sub(r"\[\[[^\]]*\]\]", "", text).strip()
    text = re.sub(r"\s*\.\.\.\s*$", "", text).strip()
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
    ]
    if sentences:
        selected: list[str] = []
        for sentence in sentences:
            candidate = " ".join(selected + [sentence]).strip()
            if len(candidate) > MAX_LIBRARY_SUMMARY_CHARS:
                break
            selected.append(sentence)
        normalized = " ".join(selected).rstrip(" ,;:") if selected else _normalize_text(text, MAX_LIBRARY_SUMMARY_CHARS).rstrip(" ,;:")
    else:
        normalized = _normalize_text(text, MAX_LIBRARY_SUMMARY_CHARS).rstrip(" ,;:")

    normalized = re.sub(
        r"\b(?:and|or|with|using|including|about|for|to|in|on|across|through|experienced in|skilled in)\s*$",
        "",
        normalized,
        flags=re.IGNORECASE,
    ).rstrip(" ,;:")
    if normalized and normalized[-1] not in ".!?":
        normalized += "."
    return normalized


def _heuristic_library_summary(clean_text: str) -> str:
    text = " ".join(clean_text.split())
    role = _detect_role(text)
    seniority = _detect_seniority(text)
    techs = _detect_technologies(text)

    if seniority and role:
        subject = f"{seniority} {role.lower()}"
    else:
        subject = seniority or role or "CV"

    if techs:
        body = f"{subject} highlighting {', '.join(techs)} experience."
    elif subject != "CV":
        body = f"{subject} with relevant project and technical experience."
    else:
        body = "Professional CV with relevant experience and technical signals."

    return _normalize_library_summary(body) or "Professional CV with relevant experience and technical signals."


def _detect_role(text: str) -> str:
    for label, pattern in ROLE_PATTERNS:
        if pattern.search(text):
            return label
    return ""


def _detect_seniority(text: str) -> str:
    for label, pattern in SENIORITY_PATTERNS:
        if pattern.search(text):
            return label
    return ""


def _detect_technologies(text: str) -> list[str]:
    found: list[str] = []
    lowered = text.lower()
    for keyword in TECH_KEYWORDS:
        if keyword.lower() in lowered and keyword not in found:
            found.append(keyword)
        if len(found) >= 4:
            break
    return found


_service: CvLibrarySummaryService | None = None


def get_cv_library_summary_service(*, fresh: bool = False) -> CvLibrarySummaryService:
    if fresh:
        return CvLibrarySummaryService()

    global _service
    if _service is None:
        _service = CvLibrarySummaryService()
    return _service
