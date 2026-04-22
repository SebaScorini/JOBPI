from __future__ import annotations

import argparse
import json
import logging
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
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
from sqlmodel import SQLModel, Session, create_engine

from app.core.ai import run_structured_ai_call, use_provider_fallback_model
from app.core.config import get_settings
from app.db import crud
from app.models.ai_schemas import CoverLetterAIOutput, CvAnalysisAIOutput, CvLibrarySummaryAIOutput, JobAnalysisAIOutput
from app.schemas.cv import CvAnalysisResponse
from app.schemas.job import AIResponseLanguage
from app.schemas.match import CVComparisonResponse, CVComparisonWinner, CVJobMatchDetailRead
from app.services.cover_letter_service import CoverLetterService, _is_meaningful_cover_letter, _normalize_cover_letter
from app.services.cv_analyzer import CvAnalyzerService, _refine_cv_analysis_response
from app.services.cv_library_service import CvLibraryService
from app.services.cv_library_summary_service import CvLibrarySummaryService, _normalize_library_summary
from app.services.job_analyzer import JobAnalyzerService, _normalize_list, _normalize_text
from app.services.job_preprocessing import build_cv_context, build_job_context, clean_description
from app.services.pdf_extractor import extract_raw_pdf_text, preprocess_cv_text
from app.services.response_language import language_instruction, normalize_language


logger = logging.getLogger(__name__)

DEFAULT_FIXTURES_ROOT = ROOT_DIR / "tests" / "fixtures" / "ai_quality_live"
DEFAULT_JOB_TITLE = "Python Engineer"
DEFAULT_COMPANY = "ETHICS CODE"
DEFAULT_LANGUAGE: AIResponseLanguage = "english"


@dataclass(slots=True)
class TraceResult:
    name: str
    raw_input: dict[str, Any]
    preprocessed_input: dict[str, Any]
    raw_prompt: Any
    model_config: dict[str, Any]
    raw_model_output: Any
    parsed_output: Any
    final_output: Any
    notes: list[str]
    score: int | None = None
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the JOBPI AI services end-to-end with real data.")
    parser.add_argument("--fixtures-root", type=Path, default=DEFAULT_FIXTURES_ROOT, help="Root folder for reusable job/CV fixtures.")
    parser.add_argument("--job", type=Path, help="Path to a job description text file.")
    parser.add_argument("--cv", action="append", type=Path, help="Path to a CV PDF. Pass multiple times to compare CVs.")
    parser.add_argument("--job-title", default=DEFAULT_JOB_TITLE, help="Job title used by the AI services.")
    parser.add_argument("--company", default=DEFAULT_COMPANY, help="Company name used by the AI services.")
    parser.add_argument("--language", choices=["english", "spanish"], default=DEFAULT_LANGUAGE, help="Response language for the AI services.")
    parser.add_argument("--output-dir", type=Path, help="Directory where snapshots and the final report will be written.")
    parser.add_argument("--user-email", default="qa@example.com", help="Temporary user email for the local test database.")
    parser.add_argument("--limit-cv-count", type=int, default=2, help="Limit how many CV PDFs are processed from the resolved set.")
    return parser.parse_args()


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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_job_file(fixtures_root: Path, explicit_job: Path | None) -> Path:
    if explicit_job is not None:
        return explicit_job

    jobs_dir = fixtures_root / "jobs"
    candidates = sorted([path for path in jobs_dir.glob("*.txt")] + [path for path in jobs_dir.glob("*.md")])
    if not candidates:
        raise FileNotFoundError(f"No job fixture found in {jobs_dir}")
    return candidates[0]


def load_cv_files(fixtures_root: Path, explicit_cvs: list[Path] | None, limit: int) -> list[Path]:
    if explicit_cvs:
        cvs = explicit_cvs
    else:
        cvs_dir = fixtures_root / "cvs"
        cvs = sorted(cvs_dir.glob("*.pdf"))
    if not cvs:
        raise FileNotFoundError("No CV PDFs were provided or found in the fixture folder.")
    return cvs[:limit]


def create_local_session(output_dir: Path, user_email: str) -> tuple[Session, Any]:
    db_path = output_dir / "ai_end_to_end.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    user = crud.create_user(session, email=user_email, hashed_password="qa-password")
    return session, user


def structure_cv_text(raw_text: str, clean_text: str) -> dict[str, Any]:
    section_map: dict[str, list[str]] = {
        "summary": [],
        "experience": [],
        "projects": [],
        "education": [],
        "skills": [],
        "certifications": [],
        "languages": [],
        "other": [],
    }
    heading = "other"

    def classify(line: str) -> str | None:
        lowered = line.lower()
        if any(token in lowered for token in ("summary", "perfil profesional", "about me", "profile")):
            return "summary"
        if any(token in lowered for token in ("experience", "employment", "work history", "professional experience")):
            return "experience"
        if any(token in lowered for token in ("project", "projects", "portfolio")):
            return "projects"
        if any(token in lowered for token in ("education", "educacion", "certification", "certifications", "coursework")):
            return "education"
        if any(token in lowered for token in ("skills", "stack", "technologies", "tools")):
            return "skills"
        if "language" in lowered or "idiom" in lowered:
            return "languages"
        if "cert" in lowered:
            return "certifications"
        return None

    for line in clean_text.splitlines():
        stripped = line.strip().strip("•-* ")
        if not stripped:
            continue
        section = classify(stripped)
        if section is not None:
            heading = section
            if stripped.lower() not in {"skills", "experience", "projects", "education", "certifications", "languages", "summary"}:
                section_map[heading].append(stripped)
            continue
        section_map[heading].append(stripped)

    issues: list[str] = []
    if len(raw_text.strip()) < 30 or not any(char.isalpha() for char in raw_text):
        issues.append("Text extraction looks unreadable or image-based.")
    if len(raw_text.splitlines()) < 10:
        issues.append("Very few extracted lines; layout may have collapsed.")
    if any(len(line) > 180 for line in clean_text.splitlines()):
        issues.append("Some extracted lines are unusually long and may contain merged columns.")
    clean_lines = clean_text.splitlines()
    if len(clean_lines) != len(set(clean_lines)):
        issues.append("Repeated fragments detected in the cleaned text.")
    if not section_map["experience"] and not section_map["projects"]:
        issues.append("No clear experience or project section was detected.")
    if not section_map["skills"]:
        issues.append("No clear skills section was detected.")

    return {
        "sections": {key: value for key, value in section_map.items() if value},
        "issues": issues,
        "raw_line_count": len(raw_text.splitlines()),
        "clean_line_count": len(clean_text.splitlines()),
    }


def save_snapshot(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def json_dump(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, default=str)


def print_section(title: str, value: Any) -> None:
    print(f"=== {title} ===")
    if isinstance(value, str):
        print(value)
    else:
        print(json_dump(value))
    print()


def model_config(*, service_name: str, model_name: str, max_tokens: int | None, retry_max_tokens: int | None, timeout_seconds: int) -> dict[str, Any]:
    settings = get_settings()
    temperature = min(max(settings.dspy_temperature, 0.25), 0.55)
    return {
        "service": service_name,
        "model": model_name,
        "fallback_model": settings.dspy_provider_fallback_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "retry_max_tokens": retry_max_tokens,
        "timeout_seconds": timeout_seconds,
    }


def trace_job_analysis(
    *,
    service: JobAnalyzerService,
    title: str,
    company: str,
    job_text: str,
    language: AIResponseLanguage,
) -> TraceResult:
    cleaned_description = clean_description(job_text)
    prompt_description = build_job_context(cleaned_description, title=title, company=company)
    selected_language = normalize_language(language)
    analyzer = service._get_analyzer()
    prompt_inputs = {
        "title": title,
        "company": company,
        "desc": prompt_description,
        "response_language": language_instruction(selected_language),
    }
    parsed = run_structured_ai_call(
        schema=JobAnalysisAIOutput,
        executor=service._executor,
        timeout_seconds=service.timeout_seconds,
        operation="job_analysis",
        logger=logger,
        callable_=analyzer,
        lm_max_tokens=service.max_tokens,
        retry_lm_max_tokens=service.retry_max_tokens,
        attempt_kwargs_builder_with_exception=lambda attempt, previous_exception: {
            "title": title,
            "company": company,
            "description": prompt_description,
            "response_language": language_instruction(selected_language),
            "max_tokens": service.max_tokens if attempt == 0 else service.retry_max_tokens,
            "model": use_provider_fallback_model(attempt, previous_exception),
        },
    )
    payload = service._build_payload_from_result(parsed.payload)
    prompt_history = capture_dspy_history() or prompt_inputs
    final_output = payload.model_dump()
    return TraceResult(
        name="job_analysis",
        raw_input={"job_text": job_text, "job_title": title, "company": company, "language": selected_language},
        preprocessed_input={"clean_description": cleaned_description, "job_context": prompt_description},
        raw_prompt=prompt_history,
        model_config=model_config(
            service_name="job_analysis",
            model_name=get_settings().dspy_model,
            max_tokens=service.max_tokens,
            retry_max_tokens=service.retry_max_tokens,
            timeout_seconds=service.timeout_seconds,
        ),
        raw_model_output=parsed.raw_output,
        parsed_output=parsed.payload.model_dump(),
        final_output=final_output,
        notes=["Job analysis stored in the local test database."],
    )


def trace_cv_library_summary(
    *,
    service: CvLibrarySummaryService,
    source_path: Path,
    clean_text: str,
) -> TraceResult:
    context = build_cv_context(clean_text, summary=first_non_empty_line(clean_text) or None)
    generator = service._create_generator()
    parsed = run_structured_ai_call(
        schema=CvLibrarySummaryAIOutput,
        executor=service._executor,
        timeout_seconds=service.timeout_seconds,
        operation="cv_library_summary",
        logger=logger,
        callable_=generator,
        lm_max_tokens=400,
        cv=context,
        max_tokens=400,
        attempt_kwargs_builder_with_exception=lambda attempt, previous_exception: {
            "cv": context,
            "max_tokens": 400,
            "model": use_provider_fallback_model(attempt, previous_exception),
        },
    )
    summary = _normalize_library_summary(parsed.payload.summary)
    prompt_history = capture_dspy_history() or {"cv": context}
    return TraceResult(
        name="cv_library_summary",
        raw_input={"source_path": str(source_path), "clean_text": clean_text},
        preprocessed_input={"cv_context": context},
        raw_prompt=prompt_history,
        model_config=model_config(
            service_name="cv_library_summary",
            model_name=get_settings().dspy_model,
            max_tokens=400,
            retry_max_tokens=None,
            timeout_seconds=service.timeout_seconds,
        ),
        raw_model_output=parsed.raw_output,
        parsed_output=parsed.payload.model_dump(),
        final_output={"summary": summary},
        notes=["Library summary generated from the cleaned CV text."],
    )


def trace_cv_analysis(
    *,
    service: CvAnalyzerService,
    source_path: Path,
    job_title: str,
    job_description: str,
    cv_text: str,
    cv_summary: str,
    cv_library_summary: str,
    language: AIResponseLanguage,
) -> TraceResult:
    job_context = build_job_context(clean_description(job_description), title=job_title)
    cv_context = build_cv_context(
        preprocess_cv_text(cv_text),
        summary=cv_summary,
        library_summary=cv_library_summary,
    )
    selected_language = normalize_language(language)
    analyzer = service._get_analyzer()
    prompt_inputs = {
        "job_title": job_title,
        "job_description": job_context,
        "cv_text": cv_context,
        "response_language": language_instruction(selected_language),
    }
    parsed = run_structured_ai_call(
        schema=CvAnalysisAIOutput,
        executor=service._executor,
        timeout_seconds=service.timeout_seconds,
        operation="cv_match_analysis",
        logger=logger,
        callable_=analyzer,
        lm_max_tokens=service.max_tokens,
        retry_lm_max_tokens=service.retry_max_tokens,
        attempt_kwargs_builder_with_exception=lambda attempt, previous_exception: {
            "job_title": job_title,
            "job_description": job_context,
            "cv_text": cv_context,
            "response_language": language_instruction(selected_language),
            "max_tokens": service.max_tokens if attempt == 0 else service.retry_max_tokens,
            "model": use_provider_fallback_model(attempt, previous_exception),
        },
    )
    response = CvAnalysisResponse(
        fit_summary=service._normalize_summary(parsed.payload.fit_summary),
        strengths=_normalize_list(parsed.payload.strengths),
        missing_skills=_normalize_list(parsed.payload.missing_skills),
        likely_fit_level=_normalize_text(parsed.payload.likely_fit_level, 20),
        resume_improvements=_normalize_list(parsed.payload.resume_improvements),
        ats_improvements=_normalize_list(getattr(parsed.payload, "ats_improvements", [])),
        recruiter_improvements=_normalize_list(getattr(parsed.payload, "recruiter_improvements", [])),
        rewritten_bullets=_normalize_list(getattr(parsed.payload, "rewritten_bullets", [])),
        interview_focus=_normalize_list(parsed.payload.interview_focus),
        next_steps=_normalize_list(parsed.payload.next_steps),
    )
    final_response = _refine_cv_analysis_response(response)
    prompt_history = capture_dspy_history() or prompt_inputs
    return TraceResult(
        name="cv_analysis",
        raw_input={"source_path": str(source_path), "job_title": job_title, "job_description": job_description, "cv_text": cv_text},
        preprocessed_input={"job_context": job_context, "cv_context": cv_context},
        raw_prompt=prompt_history,
        model_config=model_config(
            service_name="cv_match_analysis",
            model_name=get_settings().dspy_model,
            max_tokens=service.max_tokens,
            retry_max_tokens=service.retry_max_tokens,
            timeout_seconds=service.timeout_seconds,
        ),
        raw_model_output=parsed.raw_output,
        parsed_output=parsed.payload.model_dump(),
        final_output=final_response.model_dump(),
        notes=["CV analysis returned the UI-facing CvAnalysisResponse payload."],
    )


def trace_cover_letter(
    *,
    service: CoverLetterService,
    job_title: str,
    company: str,
    job_description: str,
    cv_summary: str,
    cv_text: str,
    language: AIResponseLanguage,
) -> TraceResult:
    job_context = build_job_context(clean_description(job_description), title=job_title, company=company)
    cv_context = build_cv_context(cv_text, summary=cv_summary, library_summary=cv_summary)
    selected_language = normalize_language(language)
    generator = service._get_generator()
    parsed = run_structured_ai_call(
        schema=CoverLetterAIOutput,
        executor=service._executor,
        timeout_seconds=service.timeout_seconds,
        operation="cover_letter_generation",
        logger=logger,
        callable_=generator,
        lm_max_tokens=service.max_tokens,
        attempt_kwargs_builder_with_exception=lambda attempt, previous_exception: {
            "job_title": job_title,
            "company": company,
            "job_description": job_context,
            "cv_summary": cv_summary,
            "cv_text": cv_context,
            "response_language": language_instruction(selected_language),
            "max_tokens": service.max_tokens,
            "model": use_provider_fallback_model(attempt, previous_exception),
        },
    )
    cover_letter = _normalize_cover_letter(parsed.payload.cover_letter)
    prompt_history = capture_dspy_history() or {
        "job_title": job_title,
        "company": company,
        "job_description": job_context,
        "cv_summary": cv_summary,
        "cv_text": cv_context,
        "response_language": language_instruction(selected_language),
    }
    final_output = {"generated_cover_letter": cover_letter, "is_meaningful": _is_meaningful_cover_letter(cover_letter)}
    return TraceResult(
        name="cover_letter_generation",
        raw_input={"job_title": job_title, "company": company, "job_description": job_description, "cv_summary": cv_summary, "cv_text": cv_text},
        preprocessed_input={"job_context": job_context, "cv_context": cv_context},
        raw_prompt=prompt_history,
        model_config=model_config(
            service_name="cover_letter_generation",
            model_name=get_settings().dspy_model,
            max_tokens=service.max_tokens,
            retry_max_tokens=None,
            timeout_seconds=service.timeout_seconds,
        ),
        raw_model_output=parsed.raw_output,
        parsed_output=parsed.payload.model_dump(),
        final_output=final_output,
        notes=["Cover letter stored in the local test database after generation."],
    )


def build_match_detail(
    *,
    cv_analysis: CvAnalysisResponse,
    match_object: Any,
    heuristic_score: float,
    language: AIResponseLanguage,
) -> CVJobMatchDetailRead:
    service = CvLibraryService.__new__(CvLibraryService)
    return CvLibraryService._serialize_match_detail(service, match_object, cv_analysis, heuristic_score, language)


def build_comparison_output(
    *,
    service: CvLibraryService,
    job_object: Any,
    cv_a: Any,
    match_a: CVJobMatchDetailRead,
    cv_b: Any,
    match_b: CVJobMatchDetailRead,
    language: AIResponseLanguage,
) -> CVComparisonResponse:
    winner, loser, winner_label, loser_label = service._select_better_match(
        cv_a=cv_a,
        match_a=match_a,
        cv_b=cv_b,
        match_b=match_b,
    )
    return CVComparisonResponse(
        winner=CVComparisonWinner(cv_id=winner.cv_id, label=winner_label),
        overall_reason=service._build_overall_reason(
            language=language,
            winner_label=winner_label,
            loser_label=loser_label,
            winner=winner,
            loser=loser,
        ),
        comparative_strengths=service._build_comparative_strengths(winner=winner, loser=loser),
        comparative_weaknesses=service._build_comparative_weaknesses(winner=winner, loser=loser),
        job_alignment_breakdown=service._build_job_alignment_breakdown(
            job=job_object,
            winner=winner,
            loser=loser,
            winner_label=winner_label,
            loser_label=loser_label,
            language=language,
        ),
    )


def serialize_trace(trace: TraceResult) -> dict[str, Any]:
    return {
        "name": trace.name,
        "raw_input": trace.raw_input,
        "preprocessed_input": trace.preprocessed_input,
        "raw_prompt": trace.raw_prompt,
        "model_config": trace.model_config,
        "raw_model_output": trace.raw_model_output,
        "parsed_output": trace.parsed_output,
        "final_output": trace.final_output,
        "notes": trace.notes,
        "score": trace.score,
        "error": trace.error,
    }


def print_trace(trace: TraceResult) -> None:
    print_section(f"{trace.name.upper()} | RAW INPUT", trace.raw_input)
    print_section(f"{trace.name.upper()} | PREPROCESSED INPUT", trace.preprocessed_input)
    print_section(f"{trace.name.upper()} | RAW PROMPT", trace.raw_prompt)
    print_section(f"{trace.name.upper()} | MODEL CONFIG", trace.model_config)
    print_section(f"{trace.name.upper()} | RAW MODEL OUTPUT", trace.raw_model_output)
    print_section(f"{trace.name.upper()} | PARSED OUTPUT", trace.parsed_output)
    print_section(f"{trace.name.upper()} | FINAL OUTPUT", trace.final_output)
    if trace.notes:
        print_section(f"{trace.name.upper()} | NOTES", trace.notes)


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    settings = get_settings()
    if not settings.openrouter_api_key:
        raise SystemExit("OPENROUTER_API_KEY is not set. Configure a live model before running this harness.")

    fixtures_root = args.fixtures_root.resolve()
    job_file = load_job_file(fixtures_root, args.job)
    cv_files = load_cv_files(fixtures_root, args.cv, args.limit_cv_count)
    output_dir = ensure_dir(args.output_dir or (fixtures_root / "runs" / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")))
    snapshot_dir = ensure_dir(output_dir / "snapshots")

    job_text = read_text(job_file)
    save_snapshot(snapshot_dir / f"{job_file.stem}.raw.txt", job_text)
    save_snapshot(snapshot_dir / f"{job_file.stem}.clean.txt", clean_description(job_text))

    session, user = create_local_session(output_dir, args.user_email)
    language = normalize_language(args.language)

    job_service = JobAnalyzerService()
    cv_summary_service = CvLibrarySummaryService()
    cv_analyzer_service = CvAnalyzerService()
    cv_library_service = CvLibraryService()
    cover_letter_service = CoverLetterService()

    traces: list[TraceResult] = []
    cv_records: list[Any] = []
    match_details: list[CVJobMatchDetailRead] = []
    report: dict[str, Any] = {}

    try:
        job_trace = trace_job_analysis(
            service=job_service,
            title=args.job_title,
            company=args.company,
            job_text=job_text,
            language=language,
        )
        print_trace(job_trace)
        traces.append(job_trace)

        job_payload = {**job_trace.final_output, "_language": language}
        job_record = crud.create_job_analysis(
            session,
            user_id=user.id,
            title=args.job_title,
            company=args.company,
            description=job_text,
            clean_description=clean_description(job_text),
            analysis_result=job_payload,
        )
        job_read = job_service._serialize_job(job_record)
        save_snapshot(snapshot_dir / "job_analysis.parsed.json", json_dump(job_trace.parsed_output))
        save_snapshot(snapshot_dir / "job_analysis.final.json", json_dump(job_read.model_dump()))

        for cv_path in cv_files:
            pdf_bytes = cv_path.read_bytes()
            raw_text = extract_raw_pdf_text(pdf_bytes)
            clean_text = preprocess_cv_text(raw_text)
            structured = structure_cv_text(raw_text, clean_text)
            raw_snapshot_name = cv_path.stem.replace(" ", "_")

            save_snapshot(snapshot_dir / f"{raw_snapshot_name}.raw.txt", raw_text)
            save_snapshot(snapshot_dir / f"{raw_snapshot_name}.clean.txt", clean_text)
            save_snapshot(snapshot_dir / f"{raw_snapshot_name}.structured.json", json_dump(structured))

            summary_trace = trace_cv_library_summary(service=cv_summary_service, source_path=cv_path, clean_text=clean_text)
            print_trace(summary_trace)
            traces.append(summary_trace)
            cv_summary = summary_trace.final_output["summary"]

            cv_display_name = cv_path.stem.replace("-", " ").strip()
            cv_summary_seed = first_non_empty_line(clean_text) or cv_display_name
            cv_record = crud.create_cv(
                session,
                user_id=user.id,
                filename=cv_path.name,
                display_name=cv_display_name,
                raw_text=raw_text,
                clean_text=clean_text,
                summary=cv_summary_seed,
                library_summary=cv_summary,
                tags=[],
            )
            cv_records.append(cv_record)

            cv_trace = trace_cv_analysis(
                service=cv_analyzer_service,
                source_path=cv_path,
                job_title=job_read.title,
                job_description=job_read.description,
                cv_text=clean_text,
                cv_summary=cv_summary_seed,
                cv_library_summary=cv_summary,
                language=language,
            )
            print_trace(cv_trace)
            traces.append(cv_trace)

            cv_analysis = CvAnalysisResponse.model_validate(cv_trace.final_output)
            match_fake = SimpleNamespace(
                id=0,
                user_id=user.id,
                cv_id=cv_record.id,
                job_id=job_read.id,
                fit_level=cv_analysis.likely_fit_level,
                fit_summary=cv_analysis.fit_summary,
                strengths=cv_analysis.strengths,
                missing_skills=cv_analysis.missing_skills,
                recommended=False,
                created_at=datetime.now(timezone.utc),
            )
            match_detail = build_match_detail(
                cv_analysis=cv_analysis,
                match_object=match_fake,
                heuristic_score=0.0,
                language=language,
            )
            match_details.append(match_detail)
            crud.create_match(
                session,
                user_id=user.id,
                cv_id=cv_record.id,
                job_id=job_read.id,
                fit_level=cv_analysis.likely_fit_level,
                fit_summary=cv_analysis.fit_summary,
                strengths=cv_analysis.strengths,
                missing_skills=cv_analysis.missing_skills,
                recommended=False,
            )

            save_snapshot(snapshot_dir / f"{raw_snapshot_name}.cv_analysis.json", json_dump(cv_trace.final_output))
            save_snapshot(snapshot_dir / f"{raw_snapshot_name}.match_detail.json", json_dump(match_detail.model_dump()))

        if cv_records:
            cover_letter_trace = trace_cover_letter(
                service=cover_letter_service,
                job_title=job_read.title,
                company=args.company,
                job_description=job_read.description,
                cv_summary=cv_records[0].library_summary or cv_records[0].summary,
                cv_text=cv_records[0].clean_text,
                language=language,
            )
            print_trace(cover_letter_trace)
            traces.append(cover_letter_trace)
            cover_letter_text = cover_letter_trace.final_output["generated_cover_letter"]
            crud.update_job_cover_letter(
                session,
                job=job_record,
                cv_id=cv_records[0].id,
                language=language,
                cover_letter=cover_letter_text,
            )
            save_snapshot(snapshot_dir / "cover_letter.json", json_dump(cover_letter_trace.final_output))

        comparison_trace: dict[str, Any] | None = None
        if len(cv_records) >= 2:
            comparison = build_comparison_output(
                service=cv_library_service,
                job_object=job_record,
                cv_a=cv_records[0],
                match_a=match_details[0],
                cv_b=cv_records[1],
                match_b=match_details[1],
                language=language,
            )
            comparison_trace = comparison.model_dump()
            print_section("CV COMPARISON", comparison_trace)
            save_snapshot(snapshot_dir / "compare_cvs.json", json_dump(comparison_trace))

        report = {
            "job_file": str(job_file),
            "cv_files": [str(path) for path in cv_files],
            "job_analysis": job_read.model_dump(),
            "cv_records": [cv.model_dump() for cv in cv_records],
            "match_details": [detail.model_dump() for detail in match_details],
            "comparison": comparison_trace,
            "traces": [serialize_trace(trace) for trace in traces],
        }
        save_snapshot(output_dir / "report.json", json_dump(report))

        print_section("SNAPSHOT DIRECTORY", str(snapshot_dir))
        print_section("FULL REPORT", report)
        return 0
    finally:
        session.close()
        job_service._executor.shutdown(wait=False, cancel_futures=True)
        cv_summary_service._executor.shutdown(wait=False, cancel_futures=True)
        cv_analyzer_service._executor.shutdown(wait=False, cancel_futures=True)
        cover_letter_service._executor.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    raise SystemExit(main())
