from __future__ import annotations

import argparse
import json
import sys
from contextlib import redirect_stdout
import logging
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from pprint import pformat
from types import SimpleNamespace
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.runtime import configure_runtime_environment

configure_runtime_environment()

import dspy
from app.core.ai import run_structured_ai_call
from app.core.config import get_settings
from app.models.ai_schemas import CvAnalysisAIOutput
from app.schemas.cv import CvAnalysisResponse
from app.services.cv_analyzer import CvAnalyzerService, _refine_cv_analysis_response
from app.services.cv_library_service import CvLibraryService
from app.services.job_analyzer import _normalize_list, _normalize_text
from app.services.job_preprocessing import build_cv_context, build_job_context, clean_description
from app.services.pdf_extractor import preprocess_cv_text
from app.services.response_language import language_instruction, normalize_language

logger = logging.getLogger(__name__)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def capture_dspy_history() -> str | None:
    inspector = getattr(dspy, "inspect_history", None)
    if not callable(inspector):
        return None

    attempts: list[dict[str, Any]] = [{"n": 1}, {}, {"n": 3}]
    for kwargs in attempts:
        try:
            buffer = StringIO()
            with redirect_stdout(buffer):
                result = inspector(**kwargs)
            captured = buffer.getvalue().strip()
            if captured:
                return captured
            if result is not None:
                return pformat(result, width=100)
        except TypeError:
            continue
        except Exception as exc:
            return f"<inspect_history failed: {type(exc).__name__}: {exc}>"
    return None


class EchoAnalyzer:
    def __call__(self, **kwargs):
        job_title = str(kwargs.get("job_title") or kwargs.get("title") or "the role")
        cv_text = str(kwargs.get("cv_text") or kwargs.get("cv") or "")
        if "FastAPI" in cv_text and "PostgreSQL" in cv_text:
            return SimpleNamespace(
                fit_summary=(
                    f"The CV shows strong backend fit for {job_title} with FastAPI, PostgreSQL, and observability evidence. "
                    "The main gap is broader cloud deployment scope, but the candidate has clear product delivery signals."
                ),
                strengths=[
                    "FastAPI services for workflow platforms",
                    "PostgreSQL and SQL delivery",
                    "Observability and incident diagnosis",
                    "Docker-based developer environments",
                ],
                missing_skills=[
                    "Broader cloud deployment evidence",
                    "More explicit AI or ranking-system experience",
                ],
                likely_fit_level="Strong",
                resume_improvements=["Move the matching-system project higher in the resume."],
                ats_improvements=["Repeat FastAPI and PostgreSQL wording where truthful."],
                recruiter_improvements=["Quantify incident reduction and workflow impact."],
                rewritten_bullets=["Built FastAPI APIs that supported workflow matching and reporting."],
                interview_focus=["Discuss system design tradeoffs."],
                next_steps=["Prepare a metrics-backed story about API reliability."],
            )

        return SimpleNamespace(
            fit_summary=(
                f"The CV shows web delivery experience for {job_title}, but backend evidence is thin. "
                "The strongest signals are JavaScript and team support, while the main gap is production FastAPI and PostgreSQL work."
            ),
            strengths=["JavaScript and React delivery", "Documentation support"],
            missing_skills=["Deep FastAPI evidence", "PostgreSQL architecture examples"],
            likely_fit_level="Moderate",
            resume_improvements=["Add a backend project with APIs and SQL."],
            ats_improvements=["Surface backend keywords only where they are truthful."],
            recruiter_improvements=["Show measurable ownership beyond support work."],
            rewritten_bullets=["Supported web delivery and helped coordinate releases for a small team."],
            interview_focus=["Explain any backend systems you owned."],
            next_steps=["Build one concrete backend project with metrics."],
        )


def normalize_response(service: CvAnalyzerService, parsed_payload: Any) -> CvAnalysisResponse:
    response = CvAnalysisResponse(
        fit_summary=service._normalize_summary(getattr(parsed_payload, "fit_summary", "")),
        strengths=_normalize_list(getattr(parsed_payload, "strengths", [])),
        missing_skills=_normalize_list(getattr(parsed_payload, "missing_skills", [])),
        likely_fit_level=_normalize_text(getattr(parsed_payload, "likely_fit_level", ""), 20),
        resume_improvements=_normalize_list(getattr(parsed_payload, "resume_improvements", [])),
        ats_improvements=_normalize_list(getattr(parsed_payload, "ats_improvements", [])),
        recruiter_improvements=_normalize_list(getattr(parsed_payload, "recruiter_improvements", [])),
        rewritten_bullets=_normalize_list(getattr(parsed_payload, "rewritten_bullets", [])),
        interview_focus=_normalize_list(getattr(parsed_payload, "interview_focus", [])),
        next_steps=_normalize_list(getattr(parsed_payload, "next_steps", [])),
    )
    return _refine_cv_analysis_response(response)


def build_display_output(response: CvAnalysisResponse, *, language: str) -> dict[str, Any]:
    fake_match = SimpleNamespace(
        id=1,
        user_id=1,
        cv_id=1,
        job_id=1,
        fit_level=response.likely_fit_level,
        fit_summary=response.fit_summary,
        strengths=response.strengths,
        missing_skills=response.missing_skills,
        recommended=False,
        created_at=datetime.now(timezone.utc),
    )
    service = CvLibraryService.__new__(CvLibraryService)
    detail = CvLibraryService._serialize_match_detail(service, fake_match, response, 0.42, normalize_language(language))
    return detail.model_dump()


def build_stub_result(job_title: str, cv_text: str) -> SimpleNamespace:
    analyzer = EchoAnalyzer()
    return analyzer(job_title=job_title, cv_text=cv_text)


def trace_match(
    *,
    service: CvAnalyzerService,
    job_title: str,
    job_company: str,
    job_text: str,
    cv_path: Path,
    language: str,
    dry_run: bool,
) -> dict[str, Any]:
    cv_text = read_text(cv_path)
    cv_summary = first_non_empty_line(cv_text)
    job_clean = clean_description(job_text)
    job_context = build_job_context(job_clean, title=job_title, company=job_company)
    cv_clean = preprocess_cv_text(cv_text)
    cv_context = build_cv_context(cv_clean, summary=cv_summary, library_summary=cv_summary)
    response_language = normalize_language(language)
    prompt_inputs = {
        "job_title": job_title,
        "job_description": job_context,
        "cv_text": cv_context,
        "cv_summary": cv_summary,
        "cv_library_summary": cv_summary,
        "response_language": language_instruction(response_language),
    }

    if dry_run:
        parsed_payload = build_stub_result(job_title, cv_context)
        raw_output = {
            "dry_run": True,
            "note": "No live model call was made.",
            "prompt_inputs": prompt_inputs,
        }
        prompt_history = None
    else:
        analyzer = service._get_analyzer()
        parsed = run_structured_ai_call(
            schema=CvAnalysisAIOutput,
            executor=service._executor,
            timeout_seconds=service.timeout_seconds,
            operation="ai_quality_trace",
            logger=logger,
            callable_=analyzer,
            lm_max_tokens=service.max_tokens,
            retry_lm_max_tokens=service.retry_max_tokens,
            attempt_kwargs_builder_with_exception=lambda attempt, previous_exception: {
                "job_title": job_title,
                "job_description": job_context,
                "cv_text": cv_context,
                "response_language": language_instruction(response_language),
                "max_tokens": service.max_tokens if attempt == 0 else service.retry_max_tokens,
                "model": __import__("app.core.ai", fromlist=["use_provider_fallback_model"]).use_provider_fallback_model(
                    attempt,
                    previous_exception,
                ),
            },
        )
        parsed_payload = parsed.payload
        raw_output = parsed.raw_output
        prompt_history = capture_dspy_history()

    normalized = normalize_response(service, parsed_payload)
    display = build_display_output(normalized, language=language)

    return {
        "raw_input": {
            "job_text": job_text,
            "cv_text": cv_text,
            "cv_file": str(cv_path),
            "job_title": job_title,
            "job_company": job_company,
            "cv_summary": cv_summary,
            "cv_library_summary": cv_summary,
        },
        "preprocessed_input": {
            "job_description": job_context,
            "cv_text": cv_context,
        },
        "raw_prompt": prompt_history or prompt_inputs,
        "raw_model_output": raw_output,
        "parsed_output": parsed_payload.model_dump() if hasattr(parsed_payload, "model_dump") else pformat(parsed_payload),
        "final_displayed_output": display,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect the AI response quality pipeline.")
    parser.add_argument("--job", required=True, type=Path, help="Path to the job fixture text file.")
    parser.add_argument(
        "--cv",
        required=True,
        action="append",
        type=Path,
        help="Path to a CV fixture text file. Pass more than once to compare multiple CVs.",
    )
    parser.add_argument("--job-title", default="Backend Engineer", help="Job title used in the prompt.")
    parser.add_argument("--company", default="Northstar Analytics", help="Company name used in the prompt.")
    parser.add_argument("--language", default="english", choices=["english", "spanish"], help="Response language.")
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic stub output instead of a live model.")
    args = parser.parse_args()

    job_text = read_text(args.job)
    settings = get_settings()
    service = CvAnalyzerService()

    if not args.dry_run and not settings.openrouter_api_key:
        raise SystemExit("OPENROUTER_API_KEY is not set. Re-run with --dry-run or configure the live model.")

    traces: list[tuple[Path, dict[str, Any]]] = []
    try:
        for cv_path in args.cv:
            trace = trace_match(
                service=service,
                job_title=args.job_title,
                job_company=args.company,
                job_text=job_text,
                cv_path=cv_path,
                language=args.language,
                dry_run=args.dry_run,
            )
            traces.append((cv_path, trace))
    finally:
        if not args.dry_run:
            service._executor.shutdown(wait=False, cancel_futures=True)

    print("=== RAW JOB INPUT ===")
    print(job_text)
    print()

    for cv_path, trace in traces:
        print(f"=== CV TRACE: {cv_path.name} ===")
        print("--- PREPROCESSED INPUT ---")
        print(json.dumps(trace["preprocessed_input"], indent=2, ensure_ascii=False))
        print()
        print("--- RAW PROMPT ---")
        raw_prompt = trace["raw_prompt"]
        if isinstance(raw_prompt, str):
            print(raw_prompt)
        else:
            print(json.dumps(raw_prompt, indent=2, ensure_ascii=False, default=str))
        print()
        print("--- RAW MODEL OUTPUT ---")
        print(json.dumps(trace["raw_model_output"], indent=2, ensure_ascii=False, default=str))
        print()
        print("--- PARSED OUTPUT ---")
        print(json.dumps(trace["parsed_output"], indent=2, ensure_ascii=False, default=str))
        print()
        print("--- FINAL DISPLAYED OUTPUT ---")
        print(json.dumps(trace["final_displayed_output"], indent=2, ensure_ascii=False, default=str))
        print()

    if len(traces) >= 2:
        first_cv_path, first_trace = traces[0]
        second_cv_path, second_trace = traces[1]
        print("=== COMPARISON PREVIEW ===")
        first_response = normalize_response(service, build_stub_result(args.job_title, read_text(first_cv_path))) if args.dry_run else normalize_response(service, SimpleNamespace(**first_trace["parsed_output"]))
        second_response = normalize_response(service, build_stub_result(args.job_title, read_text(second_cv_path))) if args.dry_run else normalize_response(service, SimpleNamespace(**second_trace["parsed_output"]))
        comparison = {
            "first_cv": first_cv_path.name,
            "second_cv": second_cv_path.name,
            "first_match_level": first_trace["final_displayed_output"]["match_level"],
            "second_match_level": second_trace["final_displayed_output"]["match_level"],
            "first_why_this_cv": first_trace["final_displayed_output"]["why_this_cv"],
            "second_why_this_cv": second_trace["final_displayed_output"]["why_this_cv"],
        }
        print(json.dumps(comparison, indent=2, ensure_ascii=False, default=str))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
