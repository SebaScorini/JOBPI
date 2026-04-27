import hashlib
import re

from app.core.config import get_settings
from app.core.privacy import sanitize_cv_text_for_ai


CONTEXT_BUILDER_VERSION = "2026-04-14"
ESTIMATED_CHARS_PER_TOKEN = 4
DEFAULT_JOB_EXCERPT_CHARS = 1800
DEFAULT_CV_EXCERPT_CHARS = 1800
# Hard ceilings applied AFTER noise-filtering to prevent silent AI-side
# truncation, token budget overruns, and latency spikes on long inputs.
# ~2 500 and ~2 000 tokens respectively — generous but bounded.
MAX_JOB_CONTEXT_CHARS = 10_000
MAX_CV_CONTEXT_CHARS = 8_000

_NOISE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bequal opportunity\b",
        r"\beeo\b",
        r"\ball qualified applicants\b",
        r"\bdiversity\b",
        r"\binclusion\b",
        r"\baccommodation(s)?\b",
        r"\bprivacy policy\b",
        r"\bterms of use\b",
        r"\bcompany culture\b",
        r"\bour values\b",
        r"\bbenefits\b",
        r"\bperks\b",
        r"\bcompensation\b",
        r"\bsalary\b",
        r"\babout (the )?company\b",
        r"\bwhy join us\b",
        r"\bmission\b",
        r"\bculture\b",
        r"\bwork environment\b",
        r"\bmedical\b",
        r"\b401\(k\)\b",
        r"\bparental leave\b",
        r"\bvisa sponsorship\b",
        r"\bhybrid\b",
        r"\bremote-first\b",
    ]
]

_JOB_SECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "requirements": re.compile(
        r"(requirement|qualification|must have|what you bring|what we're looking for|ideal candidate)",
        re.IGNORECASE,
    ),
    "preferred": re.compile(r"(preferred|nice to have|bonus|plus)", re.IGNORECASE),
    "responsibilities": re.compile(
        r"(responsibilit|what you('| wi)ll do|what you'll work on|day to day|key duties)",
        re.IGNORECASE,
    ),
    "role": re.compile(r"(about the role|role overview|position overview|summary)", re.IGNORECASE),
    "skills": re.compile(r"(skills?|tech stack|technology|tools?|stack)", re.IGNORECASE),
    "experience": re.compile(r"(experience|background)", re.IGNORECASE),
}
_JOB_SECTION_PRIORITY = {
    "requirements": 10,
    "responsibilities": 9,
    "skills": 8,
    "experience": 7,
    "preferred": 6,
    "role": 5,
}

_CV_SECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "summary": re.compile(r"(summary|profile|about)", re.IGNORECASE),
    "skills": re.compile(r"(skills?|technologies|stack|tools?)", re.IGNORECASE),
    "experience": re.compile(r"(experience|employment|work history)", re.IGNORECASE),
    "projects": re.compile(r"(projects?|portfolio)", re.IGNORECASE),
    "education": re.compile(r"(education|certifications?)", re.IGNORECASE),
}
_CV_SECTION_PRIORITY = {
    "summary": 10,
    "skills": 9,
    "experience": 8,
    "projects": 7,
    "education": 4,
}
_JOB_NOISE_SECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"^(benefits|perks|compensation|salary|about the company|why join us|equal opportunity.*|eeo)$",
    ]
]
_CV_NOISE_SECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"^(hobbies|interests|volunteering|activities)$",
    ]
]

_HIGH_SIGNAL_JOB_KEYWORDS = (
    "python",
    "java",
    "sql",
    "aws",
    "api",
    "backend",
    "frontend",
    "product",
    "design",
    "manage",
    "build",
    "develop",
    "experience",
    "required",
    "preferred",
    "responsible",
    "requirements",
    "responsibilities",
    "qualifications",
    "technology",
    "tools",
    "must",
    "kubernetes",
    "docker",
    "react",
    "typescript",
    "fastapi",
    "postgres",
)
_HIGH_SIGNAL_CV_KEYWORDS = (
    "python",
    "sql",
    "aws",
    "api",
    "backend",
    "frontend",
    "fastapi",
    "django",
    "flask",
    "react",
    "docker",
    "kubernetes",
    "postgres",
    "project",
    "built",
    "developed",
    "designed",
    "led",
    "launched",
    "improved",
    "delivered",
)
_ACTION_VERBS = (
    "built",
    "developed",
    "designed",
    "led",
    "launched",
    "implemented",
    "improved",
    "shipped",
    "delivered",
    "optimized",
    "owned",
)
_ROLE_KEYWORD_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+#./-]{2,}\b")


def clean_description(text: str) -> str:
    settings = get_settings()
    lines = _normalize_job_lines(text)
    compact = "\n".join(lines).strip()
    return compact[: settings.max_job_description_chars].strip()


def build_job_context(
    text: str,
    *,
    title: str | None = None,
    company: str | None = None,
    max_chars: int | None = None,
) -> str:
    lines = _normalize_job_lines(text)
    description_body = "\n".join(_format_context_lines(lines)).strip()
    # Apply a ceiling after filtering so callers and tests can override it,
    # but production is always bounded to avoid silent AI-side truncation.
    limit = max_chars if max_chars is not None else MAX_JOB_CONTEXT_CHARS
    if len(description_body) > limit:
        description_body = _truncate_at_boundary(description_body, limit)
    sections: list[str] = []
    if title and title.strip():
        sections.append(f"## Job Title\n{title.strip()}")
    if company and company.strip():
        sections.append(f"## Company\n{company.strip()}")
    sections.append(f"## Job Description\n{description_body}")
    return "\n\n".join(section for section in sections if section.strip()).strip()


def build_job_excerpt(text: str, *, max_chars: int | None = None) -> str:
    return build_job_context(text, max_chars=max_chars)


def build_cv_context(
    cv_text: str,
    *,
    summary: str | None = None,
    library_summary: str | None = None,
    max_chars: int | None = None,
) -> str:
    cv_text = sanitize_cv_text_for_ai(cv_text)
    sections: list[str] = []
    normalized_summary = _normalize_context_line(summary or "")
    normalized_library_summary = _normalize_context_line(library_summary or "")

    if normalized_summary:
        sections.append(f"## CV Summary\n{normalized_summary}")
    if normalized_library_summary and normalized_library_summary.lower() != normalized_summary.lower():
        sections.append(f"## CV Library Summary\n{normalized_library_summary}")

    lines = _normalize_cv_lines(cv_text)
    body = "\n".join(_format_context_lines(lines)).strip()
    # Apply ceiling to the body only (not to the summary headers) so that
    # the most important structured sections are always present in full.
    limit = max_chars if max_chars is not None else MAX_CV_CONTEXT_CHARS
    if len(body) > limit:
        body = _truncate_at_boundary(body, limit)
    if body:
        sections.append(f"## CV Content\n{body}")

    return "\n\n".join(section for section in sections if section.strip()).strip()


def build_cv_excerpt(
    cv_text: str,
    *,
    summary: str | None = None,
    library_summary: str | None = None,
    job_description: str | None = None,
    max_chars: int | None = None,
) -> str:
    _ = job_description
    return build_cv_context(
        cv_text,
        summary=summary,
        library_summary=library_summary,
        max_chars=max_chars,
    )


def estimate_text_tokens(text: str | None) -> int:
    if not text:
        return 0
    return max(1, (len(text) + ESTIMATED_CHARS_PER_TOKEN - 1) // ESTIMATED_CHARS_PER_TOKEN)


def estimate_payload_tokens(payload: dict[str, object]) -> int:
    return estimate_text_tokens(_stringify_payload(payload))


def build_context_fingerprint(*parts: object) -> str:
    normalized_parts = [CONTEXT_BUILDER_VERSION]
    normalized_parts.extend(_normalize_fingerprint_value(part) for part in parts)
    joined = "|".join(normalized_parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _normalize_job_lines(text: str) -> list[str]:
    normalized = re.sub(r"\r\n?", "\n", text or "")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    lines: list[str] = []
    skip_section = False
    for raw_line in normalized.split("\n"):
        line = _normalize_context_line(raw_line.strip(" -*\t"))
        if not line:
            continue
        if _is_job_noise_section_heading(line):
            skip_section = True
            continue
        if _looks_like_heading(line):
            skip_section = False
        if skip_section or _is_noise(line):
            continue
        lines.append(line)
    return _dedupe_lines(lines)


def _normalize_cv_lines(text: str) -> list[str]:
    normalized = re.sub(r"\r\n?", "\n", text or "")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    lines: list[str] = []
    skip_section = False
    for raw_line in normalized.split("\n"):
        line = _normalize_context_line(raw_line.strip(" -*\t"))
        if not line:
            continue
        if _is_cv_noise_section_heading(line):
            skip_section = True
            continue
        if _looks_like_heading(line):
            skip_section = False
        if skip_section:
            continue
        lines.append(line)
    return _dedupe_lines(lines)


def _prioritize_job_lines(lines: list[str]) -> list[str]:
    candidates: list[tuple[int, int, str]] = []
    current_section: str | None = None

    for index, line in enumerate(lines):
        heading = _match_job_section(line)
        if heading is not None:
            current_section = heading
            candidates.append((_JOB_SECTION_PRIORITY[heading] + 2, index, line.rstrip(":")))
            continue

        score = _score_job_line(line, current_section)
        if score <= 0:
            continue
        candidates.append((score, index, line))

    ordered = [line for _, _, line in sorted(candidates, key=lambda item: (-item[0], item[1]))]
    return _dedupe_lines(ordered)


def _score_job_line(line: str, current_section: str | None) -> int:
    score = _JOB_SECTION_PRIORITY.get(current_section or "", 0)
    lowered = line.lower()

    if any(pattern.search(line) for pattern in _JOB_SECTION_PATTERNS.values()):
        score += 4
    if any(keyword in lowered for keyword in _HIGH_SIGNAL_JOB_KEYWORDS):
        score += 4
    if any(token in lowered for token in ("must", "required", "responsible", "experience with")):
        score += 3
    if len(line) <= 140:
        score += 1
    return score


def _score_cv_line(line: str, *, section: str | None, role_keywords: set[str]) -> int:
    lowered = line.lower()
    score = _CV_SECTION_PRIORITY.get(section or "", 0)

    if any(keyword in lowered for keyword in _HIGH_SIGNAL_CV_KEYWORDS):
        score += 3
    if role_keywords and any(keyword in lowered for keyword in role_keywords):
        score += 4
    if any(verb in lowered for verb in _ACTION_VERBS):
        score += 2
    if re.search(r"\b\d+[%+x]?\b", line):
        score += 2
    if section == "education" and not _education_line_is_useful(line):
        score -= 2
    return score


def _dedupe_lines(lines: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()

    for line in lines:
        if not line:
            continue
        key = " ".join(line.lower().split())
        if key in seen:
            continue
        seen.add(key)
        unique.append(line)

    return unique


def _is_noise(line: str) -> bool:
    lowered = line.lower()
    if len(lowered) < 4:
        return True
    return any(pattern.search(lowered) for pattern in _NOISE_PATTERNS)


def _match_job_section(line: str) -> str | None:
    if not _looks_like_heading(line):
        return None
    for section, pattern in _JOB_SECTION_PATTERNS.items():
        if pattern.search(line):
            return section
    return None


def _match_cv_section(line: str) -> str | None:
    if len(line) > 80:
        return None
    for section, pattern in _CV_SECTION_PATTERNS.items():
        if pattern.search(line):
            return section
    return None


def _looks_like_heading(line: str) -> bool:
    if len(line) > 80:
        return False
    return line.endswith(":") or line.isupper()


def _education_line_is_useful(line: str) -> bool:
    lowered = line.lower()
    return any(
        token in lowered
        for token in ("computer", "engineering", "science", "data", "ai", "ml", "software", "aws", "cloud", "cert")
    )


def _normalize_context_line(line: str) -> str:
    return " ".join((line or "").replace("\r", " ").replace("\t", " ").split()).strip(" -")


def _format_context_lines(lines: list[str]) -> list[str]:
    formatted: list[str] = []
    for line in lines:
        heading = _heading_title(line)
        if heading is not None:
            formatted.append(f"### {heading}")
            continue
        formatted.append(f"- {line}")
    return formatted


def _heading_title(line: str) -> str | None:
    if not _looks_like_heading(line):
        return None
    cleaned = line.rstrip(":").strip()
    if not cleaned:
        return None
    return " ".join(part.capitalize() for part in cleaned.split())


def _is_job_noise_section_heading(line: str) -> bool:
    cleaned = line.rstrip(":").strip()
    return _looks_like_heading(line) and any(pattern.match(cleaned) for pattern in _JOB_NOISE_SECTION_PATTERNS)


def _is_cv_noise_section_heading(line: str) -> bool:
    cleaned = line.rstrip(":").strip()
    return _looks_like_heading(line) and any(pattern.match(cleaned) for pattern in _CV_NOISE_SECTION_PATTERNS)


def _truncate_at_boundary(text: str, limit: int) -> str:
    """Truncate *text* to at most *limit* chars, preferring a clean newline boundary."""
    if len(text) <= limit:
        return text
    cutoff = text.rfind("\n", 0, limit)
    if cutoff < int(limit * 0.75):
        # No newline in the last 25 % — fall back to the hard limit.
        cutoff = limit
    return text[:cutoff].strip()



def _join_lines_with_limit(lines: list[str], limit: int) -> str:
    selected: list[str] = []
    total = 0

    for line in lines:
        addition = len(line) + (1 if selected else 0)
        if total + addition > limit:
            continue
        selected.append(line)
        total += addition

    return "\n".join(selected)[:limit].strip()


def _truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text

    cutoff = max(
        text.rfind("\n", 0, limit),
        text.rfind(". ", 0, limit),
        text.rfind("; ", 0, limit),
    )
    if cutoff < int(limit * 0.6):
        cutoff = limit
    return text[:cutoff].strip()


def _extract_role_keywords(job_description: str) -> set[str]:
    keywords: set[str] = set()
    for token in _ROLE_KEYWORD_RE.findall(job_description or ""):
        lowered = token.lower()
        if len(lowered) < 4:
            continue
        if lowered in {"with", "from", "that", "this", "have", "will", "your", "team"}:
            continue
        if any(char.isdigit() for char in lowered):
            continue
        if lowered in _HIGH_SIGNAL_JOB_KEYWORDS:
            keywords.add(lowered)
        elif lowered[0].isalpha() and any(char in lowered for char in ("+", "#", ".", "/")):
            keywords.add(lowered)
    return keywords


def _stringify_payload(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return "\n".join(f"{key}: {_stringify_payload(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return "\n".join(_stringify_payload(item) for item in value)
    return str(value)


def _normalize_fingerprint_value(value: object) -> str:
    if isinstance(value, dict):
        items = [f"{key}={_normalize_fingerprint_value(item)}" for key, item in sorted(value.items())]
        return "{" + ",".join(items) + "}"
    if isinstance(value, (list, tuple, set)):
        return "[" + ",".join(_normalize_fingerprint_value(item) for item in value) + "]"
    return _normalize_context_line(str(value).lower())
