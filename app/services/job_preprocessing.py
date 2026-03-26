import re


MAX_DESC_CHARS = 1400
FALLBACK_DESC_CHARS = 1000
LONG_DESC_THRESHOLD = 5000

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
    ]
]

_USEFUL_SECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"responsibilit",
        r"what you('| wi)ll do",
        r"requirement",
        r"qualification",
        r"must have",
        r"preferred",
        r"nice to have",
        r"experience",
        r"skills?",
        r"tech stack",
        r"technolog",
        r"tools?",
        r"about the role",
        r"role overview",
    ]
]


def clean_description(text: str) -> str:
    normalized = re.sub(r"\r\n?", "\n", text or "")
    normalized = re.sub(r"[ \t]+", " ", normalized)

    lines = [line.strip(" -*\t") for line in normalized.split("\n")]
    lines = [line for line in lines if line]
    lines = [line for line in lines if not _is_noise(line)]

    focused = _extract_useful_sections(lines)
    compact = "\n".join(focused or lines)
    compact = re.sub(r"\n{2,}", "\n", compact).strip()

    limit = FALLBACK_DESC_CHARS if len(text or "") > LONG_DESC_THRESHOLD else MAX_DESC_CHARS
    return _truncate_text(compact, limit)


def _is_noise(line: str) -> bool:
    short = line.lower()
    if len(short) < 4:
        return True
    return any(pattern.search(short) for pattern in _NOISE_PATTERNS)


def _extract_useful_sections(lines: list[str]) -> list[str]:
    selected: list[str] = []
    in_useful_section = False

    for line in lines:
        if _looks_like_heading(line):
            in_useful_section = any(pattern.search(line) for pattern in _USEFUL_SECTION_PATTERNS)
            if in_useful_section:
                selected.append(line)
            continue

        if in_useful_section or _looks_high_signal(line):
            selected.append(line)

    return selected


def _looks_like_heading(line: str) -> bool:
    if len(line) > 80:
        return False
    return line.endswith(":") or line.isupper()


def _looks_high_signal(line: str) -> bool:
    lowered = line.lower()
    keywords = [
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
    ]
    return any(keyword in lowered for keyword in keywords)


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
