import builtins
from types import SimpleNamespace

from app.services.pdf_extractor import extract_raw_pdf_text
from app.services.pdf_extractor import preprocess_cv_text
from app.services.cv_library_summary_service import _prepare_cv_context


def test_extract_raw_pdf_text_falls_back_to_fitz_when_pypdf_missing(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pypdf":
            raise ImportError("pypdf missing")
        if name == "fitz":
            class _FakePage:
                def __init__(self, text: str) -> None:
                    self._text = text

                def get_text(self, mode: str) -> str:
                    assert mode == "text"
                    return self._text

            class _FakeDocument:
                def __enter__(self):
                    return [_FakePage("Backend engineer"), _FakePage("Python FastAPI SQL")]

                def __exit__(self, exc_type, exc, tb):
                    return False

            return SimpleNamespace(open=lambda **kwargs: _FakeDocument())
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    text = extract_raw_pdf_text(b"%PDF-1.4 fake pdf bytes")

    assert "Backend engineer" in text
    assert "Python FastAPI SQL" in text


def test_preprocess_cv_text_merges_wrapped_lines_without_cutting_sentences():
    raw = (
        "Full Stack Developer specializing in Python and FastAPI, with experience building scalable REST APIs, AI-\n"
        "powered backends using DSPy, and responsive frontends with React and\n"
        "TypeScript.\n"
        "• Built backend services with FastAPI.\n"
    )

    processed = preprocess_cv_text(raw)

    assert "AI-powered backends using DSPy" in processed
    assert "React and TypeScript." in processed
    assert "React and." not in processed


def test_prepare_cv_context_keeps_complete_lines_only():
    clean_text = "\n".join(
        [
            "Full Stack Developer specializing in Python and FastAPI.",
            "Built scalable REST APIs with DSPy and SQLModel.",
            "Developed responsive frontends with React and TypeScript.",
            "Containerized services with Docker and deployed on Vercel.",
        ]
    )

    context = _prepare_cv_context(clean_text)

    assert not context.endswith("•")
    assert "TypeScript." in context
    assert "TypeScript" in context
