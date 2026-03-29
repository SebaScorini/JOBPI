import re

from fastapi import HTTPException, status
from sqlmodel import Session

from app.db import crud
from app.models import User
from app.schemas.cv import CVDetailRead, CVRead, CvAnalysisResponse
from app.schemas.job import AIResponseLanguage
from app.schemas.match import (
    CVComparisonBetterCV,
    CVComparisonResponse,
    CVJobMatchDetailRead,
    CVJobMatchRead,
    MatchLevel,
)
from app.services.cv_analyzer import get_cv_analyzer_service
from app.services.pdf_extractor import extract_raw_pdf_text, preprocess_cv_text
from app.services.response_language import (
    localized_add_evidence,
    localized_comparison_explanation,
    localized_match_fallback,
    localized_match_prefix,
    localized_move_strength_earlier,
    localized_reorder_keyword,
    localized_reorder_strength,
    normalize_language,
)

WORD_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+#.-]{1,}\b")


class CvLibraryService:
    def __init__(self) -> None:
        self.cv_analyzer = get_cv_analyzer_service()

    def upload_cv(
        self,
        session: Session,
        user: User,
        display_name: str,
        filename: str,
        file_bytes: bytes,
    ) -> CVRead:
        # Extract and clean text once to save on downstream processing
        raw_text = extract_raw_pdf_text(file_bytes)
        cleaned_text = preprocess_cv_text(raw_text)
        # Create a simple preview summary for the library view
        summary = self._build_cv_summary(cleaned_text)
        created = crud.create_cv(
            session,
            user_id=user.id,
            filename=filename.strip(),
            display_name=display_name.strip(),
            raw_text=raw_text,
            clean_text=cleaned_text,
            summary=summary,
            tags=[],
        )
        return CVRead.model_validate(created)

    def list_cvs(self, session: Session, user: User) -> list[CVRead]:
        return [CVRead.model_validate(cv) for cv in crud.get_cvs_for_user(session, user.id)]

    def get_cv(self, session: Session, user: User, cv_id: int) -> CVDetailRead:
        cv = crud.get_cv_for_user(session, user.id, cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")
        return CVDetailRead.model_validate(cv)

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
        return CVRead.model_validate(updated)

    def match_job_to_cv(
        self,
        session: Session,
        user: User,
        job_id: int,
        cv_id: int,
        language: AIResponseLanguage = "english",
    ) -> CVJobMatchDetailRead:
        job = crud.get_job_for_user(session, user.id, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")

        cv = crud.get_cv_for_user(session, user.id, cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")

        return self._analyze_job_cv_pair(session, user, job, cv, normalize_language(language))

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

        explanation = self._build_comparison_explanation(
            language=selected_language,
            winner_label=winner_label,
            loser_label=loser_label,
            winner=winner,
            loser=loser,
        )

        return CVComparisonResponse(
            better_cv=CVComparisonBetterCV(cv_id=winner.cv_id, label=winner_label),
            explanation=explanation,
            strengths_a=match_a.strengths,
            strengths_b=match_b.strengths,
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

            result = self.cv_analyzer.analyze(
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
    ) -> CVJobMatchDetailRead:
        # Real-time AI analysis of the CV against the specific job context
        result = self.cv_analyzer.analyze(
            job_title=job.title,
            job_description=job.clean_description,
            cv_text=cv.clean_text,
            language=language,
        )
        # Quick Jaccard-like similarity for a baseline technical score
        heuristic_score = compute_heuristic_score(cv.clean_text, job.clean_description)

        # Check for existing match to avoid duplicate records if user re-triggers analysis
        existing_match = crud.get_match_for_user_by_cv_and_job(session, user.id, cv.id, job.id)
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

        return self._serialize_match_detail(existing_match, result, heuristic_score, language)

    def _select_better_match(
        self,
        cv_a: object,
        match_a: CVJobMatchDetailRead,
        cv_b: object,
        match_b: CVJobMatchDetailRead,
    ) -> tuple[CVJobMatchDetailRead, CVJobMatchDetailRead, str, str]:
        score_a = self._comparison_score(match_a)
        score_b = self._comparison_score(match_b)

        if score_a >= score_b:
            return match_a, match_b, cv_a.display_name, cv_b.display_name
        return match_b, match_a, cv_b.display_name, cv_a.display_name

    def _comparison_score(self, match: CVJobMatchDetailRead) -> float:
        level_weight = {"strong": 3.0, "medium": 2.0, "weak": 1.0}.get(match.match_level, 1.0)
        strengths_bonus = min(len(match.strengths), 4) * 0.08
        missing_penalty = min(len(match.missing_skills), 4) * 0.05
        return round(level_weight + match.heuristic_score + strengths_bonus - missing_penalty, 4)

    def _build_comparison_explanation(
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
            fallback = f"{winner_label} es el CV con mejor encaje para este puesto."
        else:
            winner_strength = winner.strengths[0] if winner.strengths else "better coverage of the role"
            loser_gap = loser.missing_skills[0] if loser.missing_skills else "fewer role-specific signals"
            fallback = f"{winner_label} is the stronger fit for this role."

        return _normalize_sentence(
            localized_comparison_explanation(
                language=language,
                winner_label=winner_label,
                loser_label=loser_label,
                winner_strength=winner_strength,
                loser_gap=loser_gap,
            ),
            fallback=fallback,
        )

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

    def _build_cv_summary(self, clean_text: str) -> str:
        parts: list[str] = []
        for line in clean_text.splitlines():
            stripped = line.strip()
            if stripped and stripped not in parts:
                parts.append(stripped)
            if len(" ".join(parts)) >= 220 or len(parts) >= 3:
                break
        summary = " ".join(parts).strip()
        if len(summary) > 220:
            summary = summary[:217].rstrip(" ,;:.") + "..."
        return summary or "CV uploaded and processed."

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
    if len(text) > 220:
        text = text[:217].rstrip(" ,;:") + "..."
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
