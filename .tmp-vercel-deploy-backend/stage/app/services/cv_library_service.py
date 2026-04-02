import re
import logging

from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.config import get_settings
from app.db import crud
from app.models import User
from app.schemas.cv import CVDetailRead, CVRead, CvAnalysisResponse
from app.schemas.job import AIResponseLanguage
from app.schemas.match import (
    CVComparisonResponse,
    CVComparisonWinner,
    CVJobMatchDetailRead,
    CVJobMatchRead,
    MatchLevel,
)
from app.services.cv_analyzer import get_cv_analyzer_service
from app.services.cv_library_summary_service import (
    get_cv_library_summary_service,
    _heuristic_library_summary,
)
from app.services.pdf_extractor import extract_raw_pdf_text, preprocess_cv_text
from app.services.response_language import (
    localized_add_evidence,
    localized_match_fallback,
    localized_match_prefix,
    localized_move_strength_earlier,
    localized_reorder_keyword,
    localized_reorder_strength,
    normalize_language,
)

WORD_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+#.-]{1,}\b")
logger = logging.getLogger(__name__)


class CvLibraryService:
    def __init__(self) -> None:
        self.cv_analyzer = None
        self.library_summary_service = None
        self._analysis_cache: dict[tuple[int, int, int, str], CvAnalysisResponse] = {}

    def upload_cv(
        self,
        session: Session,
        user: User,
        display_name: str,
        filename: str,
        file_bytes: bytes,
    ) -> CVRead:
        normalized_display_name = " ".join(display_name.split()).strip()
        normalized_filename = filename.strip() or "resume.pdf"
        if not normalized_display_name:
            raise ValueError("Display name is required.")
        if len(normalized_display_name) > 200:
            raise ValueError("Display name must be 200 characters or fewer.")
        if len(normalized_filename) > 255:
            normalized_filename = normalized_filename[:255]

        # Extract and clean text once to save on downstream processing
        settings = get_settings()
        max_cv_chars = None if settings.should_bypass_user_limits(user.email) else settings.max_cv_text_chars
        raw_text = extract_raw_pdf_text(file_bytes)
        cleaned_text = preprocess_cv_text(raw_text, max_chars=max_cv_chars)
        existing = crud.get_cv_for_user_by_clean_text(session, user.id, cleaned_text)
        if existing is not None:
            if not getattr(existing, "library_summary", "").strip():
                logger.info("ai_call operation=cv_library_summary reason=missing_summary cv_id=%s", existing.id)
                existing = crud.update_cv_library_summary(
                    session,
                    existing,
                    self._build_library_summary(cleaned_text),
                )
            else:
                logger.info("ai_cache_reuse operation=cv_library_summary source=db cv_id=%s", existing.id)
            return CVRead.model_validate(existing)

        logger.info("ai_call operation=cv_library_summary reason=new_cv")
        library_summary = self._build_library_summary(cleaned_text)
        summary = library_summary
        created = crud.create_cv(
            session,
            user_id=user.id,
            filename=normalized_filename,
            display_name=normalized_display_name,
            raw_text=raw_text,
            clean_text=cleaned_text,
            summary=summary,
            library_summary=library_summary,
            tags=[],
        )
        return CVRead.model_validate(created)

    def list_cvs(self, session: Session, user: User) -> list[CVRead]:
        return [self._serialize_cv(session, cv) for cv in crud.get_cvs_for_user(session, user.id)]

    def get_cv(self, session: Session, user: User, cv_id: int) -> CVDetailRead:
        cv = crud.get_cv_for_user(session, user.id, cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")
        enriched = self._ensure_library_summary(session, cv)
        return CVDetailRead.model_validate(enriched)

    def delete_cv(self, session: Session, user: User, cv_id: int) -> None:
        cv = crud.get_cv_for_user(session, user.id, cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")
        crud.delete_cv(session, cv)

    def update_cv_tags(self, session: Session, user: User, cv_id: int, tags: list[str]) -> CVRead:
        cv = crud.get_cv_for_user(session, user.id, cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")

        normalized_tags = self._normalize_tags(tags)
        updated = crud.update_cv_tags(session, cv, normalized_tags)
        return self._serialize_cv(session, updated)

    def match_job_to_cv(
        self,
        session: Session,
        user: User,
        job_id: int,
        cv_id: int,
        language: AIResponseLanguage = "english",
        regenerate: bool = False,
    ) -> CVJobMatchDetailRead:
        job = crud.get_job_for_user(session, user.id, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")

        cv = crud.get_cv_for_user(session, user.id, cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")

        return self._analyze_job_cv_pair(
            session,
            user,
            job,
            cv,
            normalize_language(language),
            regenerate=regenerate,
        )

    def compare_cvs_for_job(
        self,
        session: Session,
        user: User,
        job_id: int,
        cv_id_a: int,
        cv_id_b: int,
        language: AIResponseLanguage = "english",
    ) -> CVComparisonResponse:
        selected_language = normalize_language(language)
        if cv_id_a == cv_id_b:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Select two different CVs to compare.",
            )

        job = crud.get_job_for_user(session, user.id, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")

        cv_a = crud.get_cv_for_user(session, user.id, cv_id_a)
        cv_b = crud.get_cv_for_user(session, user.id, cv_id_b)
        if cv_a is None or cv_b is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")

        match_a = self._analyze_job_cv_pair(session, user, job, cv_a, selected_language)
        match_b = self._analyze_job_cv_pair(session, user, job, cv_b, selected_language)

        winner, loser, winner_label, loser_label = self._select_better_match(
            cv_a=cv_a,
            match_a=match_a,
            cv_b=cv_b,
            match_b=match_b,
        )

        overall_reason = self._build_overall_reason(
            language=selected_language,
            winner_label=winner_label,
            loser_label=loser_label,
            winner=winner,
            loser=loser,
        )
        comparative_strengths = self._build_comparative_strengths(winner=winner, loser=loser)
        comparative_weaknesses = self._build_comparative_weaknesses(winner=winner, loser=loser)
        job_alignment_breakdown = self._build_job_alignment_breakdown(
            job=job,
            winner=winner,
            loser=loser,
            winner_label=winner_label,
            loser_label=loser_label,
            language=selected_language,
        )

        return CVComparisonResponse(
            winner=CVComparisonWinner(cv_id=winner.cv_id, label=winner_label),
            overall_reason=overall_reason,
            comparative_strengths=comparative_strengths,
            comparative_weaknesses=comparative_weaknesses,
            job_alignment_breakdown=job_alignment_breakdown,
        )

    def match_job_to_all_cvs(self, session: Session, user: User, job_id: int) -> list[CVJobMatchRead]:
        job = crud.get_job_for_user(session, user.id, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")

        cvs = crud.get_cvs_for_user(session, user.id)
        if not cvs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upload at least one CV before matching.",
            )

        created_matches: list[CVJobMatchRead] = []
        scored_matches: list[tuple[float, object]] = []

        for cv in cvs:
            existing_match = crud.get_match_for_user_by_cv_and_job(session, user.id, cv.id, job.id)
            if existing_match is not None:
                score = compute_heuristic_score(cv.clean_text, job.clean_description)
                scored_matches.append((score, existing_match))
                created_matches.append(self._serialize_match(existing_match))
                continue

            result = self._analyze_pair(
                user_id=user.id,
                job_id=job.id,
                cv_id=cv.id,
                job_title=job.title,
                job_description=job.clean_description,
                cv_text=cv.clean_text,
            )
            score = compute_heuristic_score(cv.clean_text, job.clean_description)
            created = crud.create_match(
                session,
                user_id=user.id,
                cv_id=cv.id,
                job_id=job.id,
                fit_level=result.likely_fit_level,
                fit_summary=result.fit_summary,
                strengths=result.strengths,
                missing_skills=result.missing_skills,
                recommended=False,
            )
            scored_matches.append((score, created))
            created_matches.append(self._serialize_match(created))

        if scored_matches:
            # Highlight the mathematically best match based on keywords
            best_match = max(scored_matches, key=lambda item: item[0])[1]
            crud.clear_recommendations_for_job(session, user_id=user.id, job_id=job.id)
            crud.set_recommended_match(session, best_match)
            created_matches = [self._serialize_match(match) for _, match in scored_matches]

        return created_matches

    def list_matches(self, session: Session, user: User) -> list[CVJobMatchRead]:
        matches = crud.get_matches_for_user(session, user.id)
        return [self._serialize_match(match) for match in matches]

    def get_match(self, session: Session, user: User, match_id: int) -> CVJobMatchRead:
        match = crud.get_match_for_user(session, user.id, match_id)
        if match is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found.")
        return self._serialize_match(match)

    def _analyze_job_cv_pair(
        self,
        session: Session,
        user: User,
        job: object,
        cv: object,
        language: AIResponseLanguage,
        regenerate: bool = False,
    ) -> CVJobMatchDetailRead:
        existing_match = crud.get_match_for_user_by_cv_and_job(session, user.id, cv.id, job.id)
        heuristic_score = compute_heuristic_score(cv.clean_text, job.clean_description)
        result = self._get_pair_analysis_result(
            user_id=user.id,
            job_id=job.id,
            cv_id=cv.id,
            job_title=job.title,
            job_description=job.clean_description,
            cv_text=cv.clean_text,
            language=language,
            existing_match=existing_match,
            regenerate=regenerate,
        )

        if existing_match is None:
            existing_match = crud.create_match(
                session,
                user_id=user.id,
                cv_id=cv.id,
                job_id=job.id,
                fit_level=result.likely_fit_level,
                fit_summary=result.fit_summary,
                strengths=result.strengths,
                missing_skills=result.missing_skills,
                recommended=False,
            )
        elif self._match_needs_refresh(existing_match, result):
            existing_match = crud.update_match_analysis(
                session,
                existing_match,
                fit_level=result.likely_fit_level,
                fit_summary=result.fit_summary,
                strengths=result.strengths,
                missing_skills=result.missing_skills,
            )

        return self._serialize_match_detail(existing_match, result, heuristic_score, language)

    def _get_cv_analyzer(self):
        if self.cv_analyzer is None:
            self.cv_analyzer = get_cv_analyzer_service()
        return self.cv_analyzer

    def _get_library_summary_service(self):
        if self.library_summary_service is None:
            self.library_summary_service = get_cv_library_summary_service()
        return self.library_summary_service

    def _analyze_pair(
        self,
        user_id: int,
        job_id: int,
        cv_id: int,
        job_title: str,
        job_description: str,
        cv_text: str,
        language: AIResponseLanguage = "english",
    ) -> CvAnalysisResponse:
        cache_key = (user_id, job_id, cv_id, language)
        cached = self._analysis_cache.get(cache_key)
        if cached is not None:
            return cached.model_copy(deep=True)

        result = self._get_cv_analyzer().analyze(
            job_title=job_title,
            job_description=job_description,
            cv_text=cv_text,
            language=language,
        )
        self._analysis_cache[cache_key] = result.model_copy(deep=True)
        return result

    def _get_pair_analysis_result(
        self,
        user_id: int,
        job_id: int,
        cv_id: int,
        job_title: str,
        job_description: str,
        cv_text: str,
        language: AIResponseLanguage,
        existing_match: object | None,
        regenerate: bool = False,
    ) -> CvAnalysisResponse:
        if existing_match is not None and not regenerate:
            logger.info(
                "ai_cache_reuse operation=cv_match_analysis source=db user_id=%s job_id=%s cv_id=%s",
                user_id,
                job_id,
                cv_id,
            )
            return self._build_cached_match_result(existing_match, language)

        try:
            logger.info(
                "ai_call operation=cv_match_analysis user_id=%s job_id=%s cv_id=%s regenerate=%s",
                user_id,
                job_id,
                cv_id,
                regenerate,
            )
            return self._analyze_pair(
                user_id=user_id,
                job_id=job_id,
                cv_id=cv_id,
                job_title=job_title,
                job_description=job_description,
                cv_text=cv_text,
                language=language,
            )
        except HTTPException:
            if existing_match is None:
                raise
            return self._build_cached_match_result(existing_match, language)

    def _build_cached_match_result(
        self,
        match: object,
        language: AIResponseLanguage,
    ) -> CvAnalysisResponse:
        explanation = _build_match_explanation(
            fit_summary=match.fit_summary,
            strengths=list(match.strengths or []),
            missing_skills=list(match.missing_skills or []),
            improvement_suggestions=[],
            language=language,
        )
        return CvAnalysisResponse(
            fit_summary=match.fit_summary,
            strengths=list(match.strengths or []),
            missing_skills=list(match.missing_skills or []),
            likely_fit_level=match.fit_level,
            resume_improvements=explanation["suggested_improvements"],
            interview_focus=[],
            next_steps=[],
        )

    def _match_needs_refresh(self, match: object, result: CvAnalysisResponse) -> bool:
        return any(
            [
                match.fit_level != result.likely_fit_level,
                match.fit_summary != result.fit_summary,
                list(match.strengths or []) != list(result.strengths or []),
                list(match.missing_skills or []) != list(result.missing_skills or []),
            ]
        )

    def _select_better_match(
        self,
        cv_a: object,
        match_a: CVJobMatchDetailRead,
        cv_b: object,
        match_b: CVJobMatchDetailRead,
    ) -> tuple[CVJobMatchDetailRead, CVJobMatchDetailRead, str, str]:
        # Keep recommendation deterministic and aligned with the keyword-overlap score
        # used across the rest of the matching flow.
        heuristic_delta = match_a.heuristic_score - match_b.heuristic_score
        if abs(heuristic_delta) > 0.01:
            if heuristic_delta > 0:
                return match_a, match_b, cv_a.display_name, cv_b.display_name
            return match_b, match_a, cv_b.display_name, cv_a.display_name

        rank_a = self._fit_rank(match_a.match_level)
        rank_b = self._fit_rank(match_b.match_level)
        if rank_a != rank_b:
            if rank_a > rank_b:
                return match_a, match_b, cv_a.display_name, cv_b.display_name
            return match_b, match_a, cv_b.display_name, cv_a.display_name

        missing_a = len(match_a.missing_skills)
        missing_b = len(match_b.missing_skills)
        if missing_a != missing_b:
            if missing_a < missing_b:
                return match_a, match_b, cv_a.display_name, cv_b.display_name
            return match_b, match_a, cv_b.display_name, cv_a.display_name

        strengths_a = len(match_a.strengths)
        strengths_b = len(match_b.strengths)
        if strengths_a != strengths_b:
            if strengths_a > strengths_b:
                return match_a, match_b, cv_a.display_name, cv_b.display_name
            return match_b, match_a, cv_b.display_name, cv_a.display_name

        if cv_a.id <= cv_b.id:
            return match_a, match_b, cv_a.display_name, cv_b.display_name
        return match_b, match_a, cv_b.display_name, cv_a.display_name

    def _fit_rank(self, match_level: MatchLevel) -> int:
        return {"strong": 3, "medium": 2, "weak": 1}.get(match_level, 1)

    def _build_overall_reason(
        self,
        language: AIResponseLanguage,
        winner_label: str,
        loser_label: str,
        winner: CVJobMatchDetailRead,
        loser: CVJobMatchDetailRead,
    ) -> str:
        if language == "spanish":
            winner_strength = winner.strengths[0] if winner.strengths else "mejor cobertura del rol"
            loser_gap = loser.missing_skills[0] if loser.missing_skills else "senales menos especificas del puesto"
            reason = (
                f"{winner_label} muestra mejor alineacion con los requisitos clave "
                f"({winner_strength}) y menos brechas que {loser_label} ({loser_gap})."
            )
            fallback = f"{winner_label} es el CV con mejor encaje para este puesto."
        else:
            winner_strength = winner.strengths[0] if winner.strengths else "better coverage of the role"
            loser_gap = loser.missing_skills[0] if loser.missing_skills else "fewer role-specific signals"
            reason = (
                f"{winner_label} shows stronger alignment with key requirements "
                f"({winner_strength}) and fewer gaps than {loser_label} ({loser_gap})."
            )
            fallback = f"{winner_label} is the stronger fit for this role."

        return _normalize_sentence(reason, fallback=fallback)

    def _build_comparative_strengths(
        self,
        winner: CVJobMatchDetailRead,
        loser: CVJobMatchDetailRead,
    ) -> list[str]:
        winner_strengths = _clean_items(list(winner.strengths or []), limit=4)
        loser_strengths = {item.lower() for item in _clean_items(list(loser.strengths or []), limit=4)}
        unique = [item for item in winner_strengths if item.lower() not in loser_strengths]
        return (unique or winner_strengths)[:4]

    def _build_comparative_weaknesses(
        self,
        winner: CVJobMatchDetailRead,
        loser: CVJobMatchDetailRead,
    ) -> list[str]:
        loser_gaps = _clean_items(list(loser.missing_skills or []), limit=4)
        winner_gaps = {item.lower() for item in _clean_items(list(winner.missing_skills or []), limit=4)}
        unique = [item for item in loser_gaps if item.lower() not in winner_gaps]
        return (unique or loser_gaps)[:4]

    def _build_job_alignment_breakdown(
        self,
        job: object,
        winner: CVJobMatchDetailRead,
        loser: CVJobMatchDetailRead,
        winner_label: str,
        loser_label: str,
        language: AIResponseLanguage,
    ) -> list[str]:
        requirements = self._extract_job_requirements(job)
        if not requirements:
            if language == "spanish":
                winner_line = f"{winner_label}: {len(winner.strengths)} fortalezas, {len(winner.missing_skills)} brechas"
                loser_line = f"{loser_label}: {len(loser.strengths)} fortalezas, {len(loser.missing_skills)} brechas"
            else:
                winner_line = f"{winner_label}: {len(winner.strengths)} strengths, {len(winner.missing_skills)} gaps"
                loser_line = f"{loser_label}: {len(loser.strengths)} strengths, {len(loser.missing_skills)} gaps"

            return [
                _normalize_sentence(winner_line),
                _normalize_sentence(loser_line),
            ][:4]

        breakdown: list[str] = []
        for requirement in requirements[:4]:
            winner_score = self._requirement_alignment_score(requirement, winner)
            loser_score = self._requirement_alignment_score(requirement, loser)

            if winner_score > loser_score:
                if language == "spanish":
                    line = f"{requirement}: mayor alineacion en {winner_label}"
                else:
                    line = f"{requirement}: stronger match in {winner_label}"
            elif loser_score > winner_score:
                if language == "spanish":
                    line = f"{requirement}: mayor alineacion en {loser_label}"
                else:
                    line = f"{requirement}: stronger match in {loser_label}"
            else:
                if language == "spanish":
                    line = f"{requirement}: cobertura similar en ambos CVs"
                else:
                    line = f"{requirement}: similar coverage in both CVs"

            breakdown.append(_normalize_sentence(line))

        return _clean_items(breakdown, limit=4)

    def _extract_job_requirements(self, job: object) -> list[str]:
        analysis_result = getattr(job, "analysis_result", {})
        if not isinstance(analysis_result, dict):
            return []

        raw_required = analysis_result.get("required_skills", [])
        if not isinstance(raw_required, list):
            return []

        return _clean_items([item for item in raw_required if isinstance(item, str)], limit=4)

    def _requirement_alignment_score(self, requirement: str, match: CVJobMatchDetailRead) -> int:
        req_tokens = set(_tokenize(requirement))
        if not req_tokens:
            return 0

        score = 0
        for strength in match.strengths:
            if req_tokens & set(_tokenize(strength)):
                score += 2
        for gap in match.missing_skills:
            if req_tokens & set(_tokenize(gap)):
                score -= 1

        return score

    def _serialize_match(self, match: object) -> CVJobMatchRead:
        explanation = _build_match_explanation(
            fit_summary=match.fit_summary,
            strengths=list(match.strengths or []),
            missing_skills=list(match.missing_skills or []),
            improvement_suggestions=[],
        )
        return CVJobMatchRead(
            id=match.id,
            user_id=match.user_id,
            cv_id=match.cv_id,
            job_id=match.job_id,
            fit_level=match.fit_level,
            fit_summary=match.fit_summary,
            why_this_cv=explanation["why_this_cv"],
            strengths=explanation["strengths"],
            missing_skills=explanation["missing_skills"],
            improvement_suggestions=explanation["improvement_suggestions"],
            suggested_improvements=explanation["suggested_improvements"],
            missing_keywords=explanation["missing_keywords"],
            reorder_suggestions=explanation["reorder_suggestions"],
            match_level=compute_match_level(fit_level=match.fit_level),
            recommended=match.recommended,
            created_at=match.created_at,
        )

    def _serialize_match_detail(
        self,
        match: object,
        result: CvAnalysisResponse,
        heuristic_score: float,
        language: AIResponseLanguage,
    ) -> CVJobMatchDetailRead:
        base_match = self._serialize_match(match)
        base_payload = base_match.model_dump(
            exclude={
                "why_this_cv",
                "strengths",
                "missing_skills",
                "improvement_suggestions",
                "suggested_improvements",
                "missing_keywords",
                "reorder_suggestions",
                "match_level",
            }
        )
        explanation = _build_match_explanation(
            fit_summary=result.fit_summary,
            strengths=result.strengths,
            missing_skills=result.missing_skills,
            improvement_suggestions=result.resume_improvements,
            language=language,
        )
        return CVJobMatchDetailRead(
            **base_payload,
            why_this_cv=explanation["why_this_cv"],
            strengths=explanation["strengths"],
            missing_skills=explanation["missing_skills"],
            improvement_suggestions=explanation["improvement_suggestions"],
            suggested_improvements=explanation["suggested_improvements"],
            missing_keywords=explanation["missing_keywords"],
            reorder_suggestions=explanation["reorder_suggestions"],
            match_level=compute_match_level(
                fit_level=result.likely_fit_level or match.fit_level,
                heuristic_score=heuristic_score,
            ),
            heuristic_score=heuristic_score,
            result=result,
        )

    def _build_library_summary(self, clean_text: str) -> str:
        try:
            return self._get_library_summary_service().generate(clean_text)
        except Exception:
            return _heuristic_library_summary(clean_text)

    def _ensure_library_summary(self, session: Session, cv: object):
        current = getattr(cv, "library_summary", "")
        if isinstance(current, str) and current.strip():
            return cv
        return crud.update_cv_library_summary(session, cv, self._build_library_summary(cv.clean_text))

    def _serialize_cv(self, session: Session, cv: object) -> CVRead:
        enriched = self._ensure_library_summary(session, cv)
        return CVRead.model_validate(enriched)

    def _normalize_tags(self, tags: list[str]) -> list[str]:
        normalized: list[str] = []
        for tag in tags:
            if not isinstance(tag, str):
                continue
            clean_tag = " ".join(tag.split()).strip()
            if not clean_tag:
                continue
            if clean_tag not in normalized:
                normalized.append(clean_tag)
        return normalized[:20]


def compute_heuristic_score(cv_text: str, job_text: str) -> float:
    cv_tokens = set(_tokenize(cv_text))
    job_tokens = set(_tokenize(job_text))

    if not cv_tokens or not job_tokens:
        return 0.0

    union = cv_tokens | job_tokens
    score = len(cv_tokens & job_tokens) / len(union)
    return round(score, 4)


def compute_match_level(
    fit_level: str | None = None,
    heuristic_score: float | None = None,
) -> MatchLevel:
    normalized_fit = (fit_level or "").strip().lower()

    if "strong" in normalized_fit:
        return "strong"
    if "moderate" in normalized_fit or "medium" in normalized_fit:
        return "medium"
    if "weak" in normalized_fit:
        return "weak"

    score = heuristic_score or 0.0
    if score >= 0.5:
        return "strong"
    if score >= 0.25:
        return "medium"
    return "weak"


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in WORD_RE.findall(text)]


def _build_match_explanation(
    fit_summary: str,
    strengths: list[str],
    missing_skills: list[str],
    improvement_suggestions: list[str],
    language: AIResponseLanguage = "english",
) -> dict[str, object]:
    clean_strengths = _clean_items(strengths, limit=4)
    clean_missing = _clean_items(missing_skills, limit=4)
    clean_improvements = _clean_items(improvement_suggestions, limit=3)
    improvement_payload = _build_improvement_payload(
        strengths=clean_strengths,
        missing_skills=clean_missing,
        improvement_suggestions=clean_improvements,
        language=language,
    )

    why_this_cv = _normalize_sentence(fit_summary, fallback=localized_match_fallback(language))
    if clean_strengths:
        why_this_cv = _normalize_sentence(
            f"{why_this_cv.rstrip('.')} {localized_match_prefix(language)}: {', '.join(clean_strengths[:2])}.",
            fallback=why_this_cv,
        )

    return {
        "why_this_cv": why_this_cv,
        "strengths": clean_strengths,
        "missing_skills": clean_missing,
        "improvement_suggestions": improvement_payload["suggested_improvements"],
        "suggested_improvements": improvement_payload["suggested_improvements"],
        "missing_keywords": improvement_payload["missing_keywords"],
        "reorder_suggestions": improvement_payload["reorder_suggestions"],
    }


def _clean_items(items: list[str], limit: int) -> list[str]:
    cleaned: list[str] = []
    for item in items:
        normalized = _normalize_sentence(item)
        if normalized and normalized not in cleaned:
            cleaned.append(normalized)
        if len(cleaned) >= limit:
            break
    return cleaned


def _normalize_sentence(value: str, fallback: str = "") -> str:
    if not isinstance(value, str):
        return fallback

    text = " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip(" -")
    if not text:
        return fallback
    if text[-1] not in ".!?":
        text += "."
    return text


def _build_improvement_payload(
    strengths: list[str],
    missing_skills: list[str],
    improvement_suggestions: list[str],
    language: AIResponseLanguage,
) -> dict[str, object]:
    suggested_improvements = list(improvement_suggestions)
    missing_keywords = _clean_keywords(missing_skills, limit=6)

    if not suggested_improvements:
        suggested_improvements = [
            _normalize_sentence(localized_add_evidence(language, keyword), fallback="")
            for keyword in missing_keywords[:2]
        ]
        suggested_improvements = [item for item in suggested_improvements if item]
        if strengths:
            suggested_improvements.append(
                _normalize_sentence(localized_move_strength_earlier(language, strengths[0]), fallback="")
            )
        suggested_improvements = _clean_items(suggested_improvements, limit=3)

    reorder_suggestions = _build_reorder_suggestions(strengths, missing_keywords, language)

    return {
        "suggested_improvements": suggested_improvements,
        "missing_keywords": missing_keywords,
        "reorder_suggestions": reorder_suggestions or None,
    }


def _clean_keywords(items: list[str], limit: int) -> list[str]:
    cleaned: list[str] = []
    for item in items:
        keyword = _normalize_keyword(item)
        if keyword and keyword not in cleaned:
            cleaned.append(keyword)
        if len(cleaned) >= limit:
            break
    return cleaned


def _normalize_keyword(value: str) -> str:
    if not isinstance(value, str):
        return ""

    keyword = " ".join(value.replace("\r", " ").replace("\n", " ").split()).strip(" -.,;:").lower()
    if not keyword:
        return ""
    return keyword


def _build_reorder_suggestions(
    strengths: list[str],
    missing_keywords: list[str],
    language: AIResponseLanguage,
) -> list[str]:
    suggestions: list[str] = []
    if strengths:
        suggestions.append(
            _normalize_sentence(localized_reorder_strength(language, strengths[0]), fallback="")
        )
    if missing_keywords:
        suggestions.append(
            _normalize_sentence(localized_reorder_keyword(language, missing_keywords[0]), fallback="")
        )

    return [suggestion for suggestion in suggestions if suggestion][:2]


_service: CvLibraryService | None = None


def get_cv_library_service() -> CvLibraryService:
    global _service
    if _service is None:
        _service = CvLibraryService()
    return _service
