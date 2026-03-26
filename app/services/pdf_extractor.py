import logging
import re
import time

import fitz  # PyMuPDF


MAX_CV_CHARS = 800
logger = logging.getLogger(__name__)
_FILLER_LINE_RE = re.compile(
    r"\b(curriculum vitae|resume|references available|available upon request|profile|summary)\b",
    re.IGNORECASE,
)
_CONTACT_RE = re.compile(
    r"(\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b"  # email
    r"|https?://\S+"                      # URL
    r"|\+?\d[\d\s\-().]{7,}\d"           # phone
    r"|\blinkedin\.com\S*"               # linkedin
    r"|\bgithub\.com\S*)",               # github
    re.IGNORECASE,
)
_SHORT_LINE_RE = re.compile(r"^\s*(\S+\s*){1,2}\s*$")
_CV_SECTION_PATTERNS = {
    "skills": re.compile(r"\b(skills?|tech stack|technologies|tools)\b", re.IGNORECASE),
    "experience": re.compile(r"\b(experience|employment|work history|professional experience)\b", re.IGNORECASE),
    "projects": re.compile(r"\b(projects?|portfolio)\b", re.IGNORECASE),
    "education": re.compile(r"\b(education|certifications?|coursework)\b", re.IGNORECASE),
}


def extract_cv_text(file_bytes: bytes) -> str:
    """Extract and preprocess text from a PDF's raw bytes."""
    _validate_magic_bytes(file_bytes)

    extraction_start = time.perf_counter()
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages = [page.get_text() for page in doc]
        raw = "\n".join(pages)
    except Exception as exc:
        raise ValueError("Failed to read PDF content.") from exc
    finally:
        logger.info(
            "cv_fit pdf_extract_ms=%.1f",
            (time.perf_counter() - extraction_start) * 1000,
        )

    if len(raw.strip()) < 100:
        raise ValueError(
            "Could not extract text from PDF. "
            "Please ensure the file is a text-based PDF, not a scanned image."
        )

    preprocess_start = time.perf_counter()
    processed = _preprocess_cv(raw)
    logger.info(
        "cv_fit cv_preprocess_ms=%.1f",
        (time.perf_counter() - preprocess_start) * 1000,
    )
    return processed


def _validate_magic_bytes(data: bytes) -> None:
    if not data[:4] == b"%PDF":
        raise ValueError("Uploaded file is not a valid PDF.")


def _preprocess_cv(raw: str) -> str:
    normalized = re.sub(r"\r\n?", "\n", raw)
    normalized = re.sub(r"[ \t]+", " ", normalized)

    lines: list[str] = []
    for line in normalized.split("\n"):
        stripped = line.strip()
        # Drop contact noise and very short lines
        cleaned = _CONTACT_RE.sub("", stripped).strip()
        if len(cleaned) < 5:
            continue
        if _SHORT_LINE_RE.match(cleaned):
            continue
        if _FILLER_LINE_RE.search(cleaned):
            continue
        lines.append(cleaned)

    # Remove duplicate consecutive lines
    deduped: list[str] = []
    prev = ""
    for line in lines:
        if line != prev:
            deduped.append(line)
        prev = line

    focused = _extract_relevant_cv_sections(deduped)
    text = "\n".join(focused or deduped).strip()
    return _truncate_cv(text)


def _extract_relevant_cv_sections(lines: list[str]) -> list[str]:
    selected: list[str] = []
    current_section: str | None = None

    for line in lines:
        matched_section = _match_cv_section(line)
        if matched_section is not None:
            current_section = matched_section
            if matched_section != "education" or _education_line_is_useful(line):
                selected.append(line)
            continue

        if current_section in {"skills", "experience", "projects"}:
            selected.append(line)
        elif current_section == "education" and _education_line_is_useful(line):
            selected.append(line)
        elif _looks_like_high_value_cv_line(line):
            selected.append(line)

    return selected


def _match_cv_section(line: str) -> str | None:
    if len(line) > 80:
        return None

    for section, pattern in _CV_SECTION_PATTERNS.items():
        if pattern.search(line):
            return section
    return None


def _education_line_is_useful(line: str) -> bool:
    lowered = line.lower()
    return any(token in lowered for token in ("computer", "engineering", "science", "data", "ai", "ml", "software", "aws", "cloud", "cert"))


def _looks_like_high_value_cv_line(line: str) -> bool:
    lowered = line.lower()
    keywords = (
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
    )
    return any(keyword in lowered for keyword in keywords)


def _truncate_cv(text: str) -> str:
    if len(text) <= MAX_CV_CHARS:
        return text
    # Skip the first 100 chars (usually name/address block)
    start = min(100, len(text) // 4)
    excerpt = text[start: start + MAX_CV_CHARS]
    cutoff = excerpt.rfind("\n")
    if cutoff < int(MAX_CV_CHARS * 0.6):
        cutoff = MAX_CV_CHARS
    return excerpt[:cutoff].strip()
