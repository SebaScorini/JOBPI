from __future__ import annotations

import re
from typing import Any


EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"\+?\d[\d\s\-().]{7,}\d")
URL_RE = re.compile(r"(https?://\S+|\b(?:linkedin|github)\.com/\S+)", re.IGNORECASE)
ADDRESS_RE = re.compile(
    r"\b\d{1,6}\s+[A-Za-z0-9.'\- ]+\s(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|way|court|ct)\b",
    re.IGNORECASE,
)
POSTAL_LINE_RE = re.compile(r"\b\d{4,10}\b")
NAME_LINE_RE = re.compile(r"^[A-Z][a-z]+(?: [A-Z][a-z'.-]+){1,4}$")

PROMPT_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bignore (all |any )?(previous|prior) instructions\b",
        r"\bdisregard (all |any )?(previous|prior) instructions\b",
        r"\b(system|assistant|developer|user|tool)\s*:",
        r"\byou are (chatgpt|an ai|a language model|an assistant)\b",
        r"\bnew instructions\b",
        r"\boverride\b.*\binstructions\b",
        r"\bdo not follow the above\b",
        r"\bprompt injection\b",
    )
]

HIGH_SIGNAL_CV_TOKENS = {
    "python",
    "sql",
    "aws",
    "api",
    "backend",
    "frontend",
    "react",
    "fastapi",
    "docker",
    "kubernetes",
    "project",
    "experience",
    "skills",
    "education",
    "summary",
}


def redact_text(value: str) -> str:
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = URL_RE.sub("[REDACTED_URL]", text)
    text = ADDRESS_RE.sub("[REDACTED_ADDRESS]", text)
    return text


def redact_pii(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_pii(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_pii(item) for item in value)
    if isinstance(value, dict):
        return {key: redact_pii(item) for key, item in value.items()}
    return value


def redact_email_for_observability(email: str | None) -> str | None:
    if not email:
        return None
    normalized = email.strip().lower()
    if not normalized:
        return None
    local, _, domain = normalized.partition("@")
    if not domain:
        return "[REDACTED_EMAIL]"
    prefix = local[:1] or "*"
    return f"{prefix}***@{domain}"
def sanitize_cv_text_for_ai(text: str) -> str:
    sanitized_lines: list[str] = []
    for index, raw_line in enumerate(text.splitlines()):
        line = redact_text(raw_line).strip()
        if not line:
            continue
        if _looks_like_prompt_injection(line):
            continue
        if _looks_like_personal_header_line(line, index=index):
            continue
        sanitized_lines.append(line)
    return "\n".join(sanitized_lines).strip()


def summarize_redacted_payload(value: object, *, limit: int = 8) -> str:
    if isinstance(value, dict):
        keys = list(value.keys())[:limit]
        return f"<dict keys={','.join(str(key) for key in keys)}>"
    if isinstance(value, list):
        return f"<list len={len(value)}>"
    if isinstance(value, tuple):
        return f"<tuple len={len(value)}>"
    if value is None:
        return "<none>"
    return f"<{type(value).__name__}>"


def _looks_like_prompt_injection(line: str) -> bool:
    return any(pattern.search(line) for pattern in PROMPT_INJECTION_PATTERNS)


def _looks_like_personal_header_line(line: str, *, index: int) -> bool:
    lowered = line.lower()
    if any(token in lowered for token in HIGH_SIGNAL_CV_TOKENS):
        return False
    if index <= 2 and NAME_LINE_RE.match(line):
        return True
    if "[REDACTED_ADDRESS]" in line:
        return True
    if POSTAL_LINE_RE.search(line) and any(token in lowered for token in ("city", "state", "zip", "postal", "address")):
        return True
    return False
