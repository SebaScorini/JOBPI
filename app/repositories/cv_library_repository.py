from __future__ import annotations

from sqlmodel import Session

from app.db import crud
from app.models import CV


class CvLibraryRepository:
    """Data access boundary used by CvLibraryService."""

    def get_cv_for_user_by_clean_text(self, session: Session, user_id: int, clean_text: str) -> CV | None:
        return crud.get_cv_for_user_by_clean_text(session, user_id, clean_text)

    def update_cv_library_summary(self, session: Session, cv: CV, library_summary: str) -> CV:
        return crud.update_cv_library_summary(session, cv, library_summary)

    def create_cv(
        self,
        session: Session,
        *,
        user_id: int,
        filename: str,
        display_name: str,
        raw_text: str,
        clean_text: str,
        summary: str,
        library_summary: str,
        tags: list[str] | None = None,
    ) -> CV:
        return crud.create_cv(
            session,
            user_id=user_id,
            filename=filename,
            display_name=display_name,
            raw_text=raw_text,
            clean_text=clean_text,
            summary=summary,
            library_summary=library_summary,
            tags=tags,
        )

    def list_cvs_for_user(self, session: Session, user_id: int, *, limit: int, offset: int) -> tuple[list[CV], int]:
        return crud.get_cvs_for_user(session, user_id, limit=limit, offset=offset)

    def get_cvs_for_user(self, session: Session, user_id: int, *, limit: int, offset: int) -> tuple[list[CV], int]:
        return self.list_cvs_for_user(session, user_id, limit=limit, offset=offset)

    def list_cvs_filtered(
        self,
        session: Session,
        user_id: int,
        *,
        search: str,
        tags: list[str] | None,
        limit: int,
        offset: int,
    ) -> tuple[list[CV], int]:
        return crud.get_filtered_cvs_for_user(
            session,
            user_id,
            search=search,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def get_filtered_cvs_for_user(
        self,
        session: Session,
        user_id: int,
        *,
        search: str,
        tags: list[str] | None,
        limit: int,
        offset: int,
    ) -> tuple[list[CV], int]:
        return self.list_cvs_filtered(
            session,
            user_id,
            search=search,
            tags=tags,
            limit=limit,
            offset=offset,
        )

    def get_cv_for_user(self, session: Session, user_id: int, cv_id: int) -> CV | None:
        return crud.get_cv_for_user(session, user_id, cv_id)

    def delete_cv(self, session: Session, cv: CV) -> None:
        crud.delete_cv(session, cv)

    def update_cv_tags(self, session: Session, cv: CV, tags: list[str]) -> CV:
        return crud.update_cv_tags(session, cv, tags)

    def update_cv_favorite(self, session: Session, cv: CV, is_favorite: bool) -> CV:
        return crud.update_cv_favorite(session, cv, is_favorite)

    def get_cvs_for_user_by_ids(self, session: Session, user_id: int, cv_ids: list[int]) -> list[CV]:
        return crud.get_cvs_for_user_by_ids(session, user_id, cv_ids)

    def delete_multiple_cvs(self, session: Session, cvs: list[CV]) -> int:
        return crud.delete_multiple_cvs(session, cvs)

    def update_multiple_cv_tags(self, session: Session, cvs: list[CV], tags: list[str]) -> int:
        return crud.update_multiple_cv_tags(session, cvs, tags)

    def update_cv_storage_path(self, session: Session, cv: CV, storage_path: str | None) -> CV:
        return crud.update_cv_storage_path(session, cv, storage_path)
