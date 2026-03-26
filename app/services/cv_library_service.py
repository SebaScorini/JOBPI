import hashlib
import json
import re

from fastapi import HTTPException, status
from sqlmodel import Session

from app.db import crud
from app.schemas.cv import CvAnalysisResponse
from app.schemas.library import (
    CVJobMatchRead,
    RecommendationCVRead,
    RecommendationMatchRead,
    RecommendationRead,
    StoredCVRead,
)
from app.services.cv_analyzer import get_cv_analyzer_service
from app.services.pdf_extractor import extract_cv_text

WORD_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+#.-]{1,}\b")


class CvLibraryService:
    def __init__(self) -> None:
        self.cv_analyzer = get_cv_analyzer_service()

    def upload_cv(self, session: Session, name: str, file_bytes: bytes) -> StoredCVRead:
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        existing = crud.get_cv_by_hash(session, file_hash)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"That CV already exists in the library (id: {existing.id}).",
            )

        cleaned_text = extract_cv_text(file_bytes)
        created = crud.create_cv(session, name=name.strip(), file_hash=file_hash, cleaned_text=cleaned_text)
        return StoredCVRead.model_validate(created)

    def list_cvs(self, session: Session) -> list[StoredCVRead]:
        return [StoredCVRead.model_validate(cv) for cv in crud.get_all_cvs(session)]

    def get_cv(self, session: Session, cv_id: int) -> StoredCVRead:
        cv = crud.get_cv(session, cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")
        return StoredCVRead.model_validate(cv)

    def delete_cv(self, session: Session, cv_id: int) -> None:
        cv = crud.get_cv(session, cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")
        crud.delete_cv(session, cv)

    def match_cv_to_job(self, session: Session, cv_id: int, job_id: int) -> CVJobMatchRead:
        cv = crud.get_cv(session, cv_id)
        if cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CV not found.")

        job = crud.get_job(session, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")

        existing_match = crud.get_match(session, cv_id, job_id)
        if existing_match is not None:
            return self._serialize_match(existing_match)

        result = self.cv_analyzer.analyze(
            job_title=job.title,
            job_description=job.cleaned_description,
            cv_text=cv.cleaned_text,
        )
        heuristic_score = compute_heuristic_score(cv.cleaned_text, job.cleaned_description)
        created = crud.create_match(
            session,
            cv_id=cv_id,
            job_id=job_id,
            result_json=json.dumps(result.model_dump()),
            heuristic_score=heuristic_score,
        )
        return self._serialize_match(created)

    def recommend_best_cv(self, session: Session, job_id: int) -> RecommendationRead:
        job = crud.get_job(session, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job analysis not found.")

        matches = crud.get_all_matches_for_job(session, job_id)
        if not matches:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No CV matches found for this job. Run /library/match first.",
            )

        ranked = sorted(matches, key=lambda item: item.heuristic_score, reverse=True)
        best_match = ranked[0]
        best_cv = crud.get_cv(session, best_match.cv_id)
        if best_cv is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommended CV not found.")

        return RecommendationRead(
            best_cv=RecommendationCVRead(id=best_cv.id, name=best_cv.name),
            score=best_match.heuristic_score,
            matches=[RecommendationMatchRead(cv_id=match.cv_id, score=match.heuristic_score) for match in ranked],
        )

    def _serialize_match(self, match) -> CVJobMatchRead:
        return CVJobMatchRead(
            id=match.id,
            cv_id=match.cv_id,
            job_id=match.job_id,
            heuristic_score=match.heuristic_score,
            result=CvAnalysisResponse.model_validate_json(match.result_json),
            created_at=match.created_at,
        )


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
