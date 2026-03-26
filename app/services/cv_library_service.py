import re

from fastapi import HTTPException, status
from sqlmodel import Session

from app.db import crud
from app.models import User
from app.schemas.cv import CVDetailRead, CVRead, CvAnalysisResponse
from app.schemas.match import CVJobMatchDetailRead, CVJobMatchRead
from app.services.cv_analyzer import get_cv_analyzer_service
from app.services.pdf_extractor import extract_raw_pdf_text, preprocess_cv_text

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
        raw_text = extract_raw_pdf_text(file_bytes)
        cleaned_text = preprocess_cv_text(raw_text)
        summary = self._build_cv_summary(cleaned_text)
        created = crud.create_cv(
            session,
            user_id=user.id,
            filename=filename.strip(),
            display_name=display_name.strip(),
            raw_text=raw_text,
            clean_text=cleaned_text,
            summary=summary,
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

    def match_job_to_cv(
        self,
        session: Session,
        user: User,
        job_id: int,
        cv_id: int,
    ) -> CVJobMatchDetailRead:
        job = crud.get_job_for_user(session, user.id, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")

        cv = crud.get_cv_for_user(session, user.id, cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")

        result = self.cv_analyzer.analyze(
            job_title=job.title,
            job_description=job.clean_description,
            cv_text=cv.clean_text,
        )
        heuristic_score = compute_heuristic_score(cv.clean_text, job.clean_description)

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

        return self._serialize_match_detail(existing_match, result, heuristic_score)

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
            best_match = max(scored_matches, key=lambda item: item[0])[1]
            crud.clear_recommendations_for_job(session, user.id, job.id)
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

    def _serialize_match(self, match: object) -> CVJobMatchRead:
        return CVJobMatchRead(
            id=match.id,
            user_id=match.user_id,
            cv_id=match.cv_id,
            job_id=match.job_id,
            fit_level=match.fit_level,
            fit_summary=match.fit_summary,
            strengths=list(match.strengths or []),
            missing_skills=list(match.missing_skills or []),
            recommended=match.recommended,
            created_at=match.created_at,
        )

    def _serialize_match_detail(
        self,
        match: object,
        result: CvAnalysisResponse,
        heuristic_score: float,
    ) -> CVJobMatchDetailRead:
        base_match = self._serialize_match(match)
        return CVJobMatchDetailRead(
            **base_match.model_dump(),
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


def compute_heuristic_score(cv_text: str, job_text: str) -> float:
    cv_tokens = set(_tokenize(cv_text))
    job_tokens = set(_tokenize(job_text))

    if not cv_tokens or not job_tokens:
        return 0.0

    union = cv_tokens | job_tokens
    score = len(cv_tokens & job_tokens) / len(union)
    return round(score, 4)


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in WORD_RE.findall(text)]


_service: CvLibraryService | None = None


def get_cv_library_service() -> CvLibraryService:
    global _service
    if _service is None:
        _service = CvLibraryService()
    return _service
