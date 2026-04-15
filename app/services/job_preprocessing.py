import hashlib
import re

from app.core.config import get_settings


CONTEXT_BUILDER_VERSION = "2026-04-14"
ESTIMATED_CHARS_PER_TOKEN = 4
DEFAULT_JOB_EXCERPT_CHARS = 1800
DEFAULT_CV_EXCERPT_CHARS = 1800

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
    focused = _prioritize_job_lines(lines)
    compact = "\n".join(focused or lines).strip()

    hard_limit = settings.max_job_description_chars
    target_limit = min(hard_limit, settings.job_preprocess_target_chars)
    long_desc_threshold = max(target_limit, 5000)
    limit = target_limit if len(text or "") > long_desc_threshold else hard_limit
    return _truncate_text(compact, limit)


def build_job_excerpt(text: str, *, max_chars: int | None = None) -> str:
    settings = get_settings()
    limit = min(
        settings.max_job_description_chars,
        max_chars if max_chars is not None else min(settings.job_preprocess_target_chars, DEFAULT_JOB_EXCERPT_CHARS),
    )
    lines = _normalize_job_lines(text)
    excerpt = "\n".join(_prioritize_job_lines(lines) or lines)
    return _truncate_text(excerpt, limit)


def build_cv_excerpt(
    cv_text: str,
    *,
    summary: str | None = None,
    library_summary: str | None = None,
    job_description: str | None = None,
    max_chars: int | None = None,
) -> str:
    settings = get_settings()
    limit = min(
        settings.max_cv_text_chars,
        max_chars if max_chars is not None else DEFAULT_CV_EXCERPT_CHARS,
    )
    role_keywords = _extract_role_keywords(job_description or "")

    candidates: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    index = 0

    for text_value, score in ((summary, 15), (library_summary, 14)):
        normalized = _normalize_context_line(text_value or "")
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        candidates.append((score, index, normalized))
        index += 1

    current_section: str | None = None
    for raw_line in (cv_text or "").splitlines():
        line = _normalize_context_line(raw_line)
        if not line:
            continue

        heading = _match_cv_section(line)
        if heading is not None:
            current_section = heading
            if current_section in {"skills", "experience", "projects"}:
                heading_line = line.rstrip(":")
                key = heading_line.lower()
                if key not in seen:
                    seen.add(key)
                    candidates.append((_CV_SECTION_PRIORITY[current_section] + 1, index, heading_line))
                    index += 1
            continue
        if _looks_like_heading(line):
            current_section = None
            continue

        if _is_noise(line):
            continue

        score = _score_cv_line(line, section=current_section, role_keywords=role_keywords)
        if score <= 0:
            continue

        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        candidates.append((score, index, line))
        index += 1

    ordered = [line for _, _, line in sorted(candidates, key=lambda item: (-item[0], item[1]))]
    return _join_lines_with_limit(ordered, limit)


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
    lines = [_normalize_context_line(line.strip(" -*\t")) for line in normalized.split("\n")]
    return [line for line in _dedupe_lines(lines) if line and not _is_noise(line)]


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
