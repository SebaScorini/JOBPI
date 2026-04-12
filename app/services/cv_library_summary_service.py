import re
import logging
from concurrent.futures import ThreadPoolExecutor

from app.core.runtime import configure_runtime_environment

configure_runtime_environment()

import dspy
from fastapi import HTTPException, status

from app.core.ai import dspy_lm_override, run_ai_call_with_circuit_breaker
from app.core.config import configure_dspy, get_settings
from app.services.job_analyzer import _normalize_text


# Keep the old symbol name available for tests and local monkeypatching.
run_ai_call_with_timeout = run_ai_call_with_circuit_breaker


MAX_LIBRARY_SUMMARY_CHARS = 180
MAX_LIBRARY_CONTEXT_CHARS = 650
SUMMARY_MAX_TOKENS = 372
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
    """Generate a compact CV card summary.

    Include only role/seniority (if clear) and key technologies from the CV.
    No filler, generic claims, or invented details.
    """

    cv: str = dspy.InputField(desc="Clean CV excerpt")
    summary: str = dspy.OutputField(
        desc="1-2 short sentences max. Mention profile + key technologies only if evidenced."
    )


class CvLibrarySummaryModule(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(CvLibrarySummarySignature)

    def forward(self, cv: str, max_tokens: int | None = None):
        predict_kwargs = {
            "cv": cv,
            # Keep library summaries isolated per CV upload. Reusing cached LM
            # responses here can surface stale summaries across batch uploads.
            "config": {"cache": False},
        }
        if max_tokens is None:
            return self.predict(**predict_kwargs)

        with dspy_lm_override(max_tokens=max_tokens):
            return self.predict(**predict_kwargs)


class CvLibrarySummaryService:
    def __init__(self) -> None:
        settings = get_settings()
        self.timeout_seconds = max(10, min(settings.ai_timeout_seconds, 30))
        self._executor = ThreadPoolExecutor(max_workers=2)

    def generate(self, clean_text: str) -> str:
        context = _prepare_cv_context(clean_text)
        if not context:
            logger.info("ai_cache_reuse operation=cv_library_summary source=heuristic_empty_context")
            return _heuristic_library_summary(clean_text)

        try:
            generator = self._create_generator()
            logger.info("ai_call operation=cv_library_summary")
            result = run_ai_call_with_timeout(
                executor=self._executor,
                timeout_seconds=self.timeout_seconds,
                operation="cv_library_summary",
                logger=logger,
                callable_=generator,
                lm_max_tokens=SUMMARY_MAX_TOKENS,
                cv=context,
                max_tokens=SUMMARY_MAX_TOKENS,
            )
            summary = _normalize_library_summary(result.summary)
            if summary:
                return summary
        except HTTPException:
            logger.warning("cv_library_summary_fallback reason=timeout_or_http")
        except Exception:
            logger.exception("cv_library_summary_fallback reason=unexpected_error")

        logger.info("ai_cache_reuse operation=cv_library_summary source=heuristic_fallback")
        return _heuristic_library_summary(clean_text)

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
    parts: list[str] = []
    seen: set[str] = set()
    char_count = 0

    for raw_line in clean_text.splitlines():
        line = " ".join(raw_line.split()).strip(" -")
        if not line:
            continue
        lowered = line.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        parts.append(line)
        char_count += len(line) + 1
        if len(parts) >= 10 or char_count >= MAX_LIBRARY_CONTEXT_CHARS:
            break

    return "\n".join(parts)[:MAX_LIBRARY_CONTEXT_CHARS].strip()


def _normalize_library_summary(value: object) -> str:
    if not isinstance(value, str):
        return ""

    text = " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip(" \"'-")
    if not text:
        return ""

    text = re.sub(r"\[\[[^\]]*\]\]", "", text).strip()
    text = re.sub(r"\s*\.\.\.\s*$", "", text).strip()
    normalized = _normalize_text(text, MAX_LIBRARY_SUMMARY_CHARS).rstrip(" ,;:")
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
