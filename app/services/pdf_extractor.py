import logging
import re
import time
from io import BytesIO

from app.core.config import get_settings
from app.core.privacy import sanitize_cv_text_for_ai

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
_TEXT_SIGNAL_RE = re.compile(r"[A-Za-z]")
_CV_SECTION_PATTERNS = {
    "skills": re.compile(r"\b(skills?|tech stack|technologies|tools)\b", re.IGNORECASE),
    "experience": re.compile(r"\b(experience|employment|work history|professional experience)\b", re.IGNORECASE),
    "projects": re.compile(r"\b(projects?|portfolio)\b", re.IGNORECASE),
    "education": re.compile(r"\b(education|certifications?|coursework)\b", re.IGNORECASE),
}


def extract_cv_text(file_bytes: bytes, max_chars: int | None = None) -> str:
    """Extract and preprocess text from a PDF's raw bytes."""
    raw = extract_raw_pdf_text(file_bytes)
    return preprocess_cv_text(raw, max_chars=max_chars)


def extract_raw_pdf_text(file_bytes: bytes) -> str:
    _validate_magic_bytes(file_bytes)

    extraction_start = time.perf_counter()
    try:
        raw = _extract_with_available_pdf_backend(file_bytes)
    except Exception as exc:
        if isinstance(exc, ValueError):
            raise
        raise ValueError("Failed to read PDF content.") from exc
    finally:
        logger.info(
            "cv_fit pdf_extract_ms=%.1f",
            (time.perf_counter() - extraction_start) * 1000,
        )

    stripped = raw.strip()
    if len(stripped) < 30 or not _TEXT_SIGNAL_RE.search(stripped):
        raise ValueError(
            "Could not extract text from PDF. "
            "Please ensure the file is a text-based PDF, not a scanned image."
        )
    return raw


def preprocess_cv_text(raw: str, max_chars: int | None = None) -> str:
    preprocess_start = time.perf_counter()
    processed = _preprocess_cv(raw, max_chars=max_chars)
    logger.info(
        "cv_fit cv_preprocess_ms=%.1f",
        (time.perf_counter() - preprocess_start) * 1000,
    )
    return processed


def _validate_magic_bytes(data: bytes) -> None:
    if len(data) < 8 or not data[:4] == b"%PDF":
        raise ValueError("Uploaded file is not a valid PDF.")


def _extract_with_available_pdf_backend(file_bytes: bytes) -> str:
    pypdf_import_error: Exception | None = None
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(file_bytes))
        if getattr(reader, "is_encrypted", False):
            raise ValueError("Encrypted PDFs are not supported.")
        if len(reader.pages) == 0:
            raise ValueError("Uploaded PDF has no readable pages.")
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except ImportError as exc:
        pypdf_import_error = exc

    try:
        import fitz

        with fitz.open(stream=file_bytes, filetype="pdf") as document:
            if getattr(document, "needs_pass", False):
                raise ValueError("Encrypted PDFs are not supported.")
            page_count = getattr(document, "page_count", None)
            if page_count is not None and page_count <= 0:
                raise ValueError("Uploaded PDF has no readable pages.")
            return "\n".join(page.get_text("text") or "" for page in document)
    except ImportError as exc:
        if pypdf_import_error is not None:
            raise ValueError("PDF support is not installed on the server.") from pypdf_import_error
        raise ValueError("PDF support is not installed on the server.") from exc


def _preprocess_cv(raw: str, max_chars: int | None = None) -> str:
    normalized = re.sub(r"\r\n?", "\n", raw)
    normalized = re.sub(r"(?<=\w)-\n(?=\w)", "-", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)

    lines: list[str] = []
    for line in normalized.split("\n"):
        stripped = line.strip()
        cleaned = _CONTACT_RE.sub("", stripped).strip()
        if cleaned:
            lines.append(cleaned)

    lines = _merge_wrapped_lines(lines)
    lines = [
        line
        for line in lines
        if len(line) >= 5 and not _SHORT_LINE_RE.match(line) and not _FILLER_LINE_RE.search(line)
    ]

    # Remove duplicate consecutive lines
    deduped: list[str] = []
    prev = ""
    for line in lines:
        if line != prev:
            deduped.append(line)
        prev = line

    focused = _extract_relevant_cv_sections(deduped)
    text = sanitize_cv_text_for_ai("\n".join(focused or deduped).strip())
    return _truncate_cv(text, max_chars=max_chars)


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


def _truncate_cv(text: str, max_chars: int | None = None) -> str:
    max_cv_chars = max_chars if max_chars is not None else get_settings().max_cv_text_chars

    if len(text) <= max_cv_chars:
        return text
    excerpt = text[:max_cv_chars]
    cutoff = excerpt.rfind("\n")
    if cutoff < int(max_cv_chars * 0.6):
        cutoff = max_cv_chars
    return excerpt[:cutoff].strip()


def _merge_wrapped_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []

    for line in lines:
        if (
            merged
            and _looks_like_wrapped_continuation(previous=merged[-1], current=line)
        ):
            merged[-1] = f"{merged[-1].rstrip()} {line.lstrip()}".strip()
        else:
            merged.append(line)

    return merged


def _looks_like_wrapped_continuation(*, previous: str, current: str) -> bool:
    if not previous or not current:
        return False
    if previous.endswith((".", ":", ";", "!", "?")):
        return False
    if previous.lstrip().startswith("•") and current.lstrip().startswith("•"):
        return False
    if current.lstrip().startswith(("•", "-", "*")):
        return False
    return current[:1].islower() or previous.endswith(("and", "or", "/", "with", "using"))
