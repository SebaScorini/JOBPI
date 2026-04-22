import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy import func, update
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from sqlmodel import Session, select

from app.models import CV, CVJobMatch, JobAnalysis, User
from app.services.supabase_storage import SupabaseStorageError, get_supabase_storage_service


logger = logging.getLogger(__name__)


def _is_postgres_session(session: Session) -> bool:
    bind = session.get_bind()
    return bind is not None and bind.dialect.name == "postgresql"


CV_LIST_COLUMNS = (
    CV.id,
    CV.filename,
    CV.display_name,
    CV.summary,
    CV.library_summary,
    CV.storage_path,
    CV.is_favorite,
    CV.tags,
    CV.created_at,
)

JOB_LIST_COLUMNS = (
    JobAnalysis.id,
    JobAnalysis.title,
    JobAnalysis.company,
    JobAnalysis.description,
    JobAnalysis.clean_description,
    JobAnalysis.analysis_result,
    JobAnalysis.is_saved,
    JobAnalysis.status,
    JobAnalysis.applied_date,
    JobAnalysis.notes,
    JobAnalysis.created_at,
)


def _group_cv_ids_by_user(cvs: list[CV]) -> dict[int, list[int]]:
    grouped: dict[int, list[int]] = {}
    for cv in cvs:
        if cv.id is None:
            continue
        grouped.setdefault(cv.user_id, []).append(cv.id)
    return grouped


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _postgres_sha256_expr(column):
    return func.encode(func.digest(column, "sha256"), "hex")


def create_user(session: Session, email: str, hashed_password: str) -> User:
    user = User(email=email.lower().strip(), hashed_password=hashed_password)
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise ValueError("A user with that email already exists.") from exc
    session.refresh(user)
    return user


def get_user_by_email(session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email.lower().strip(), User.deleted_at.is_(None))
    return session.exec(statement).first()


def get_user_by_id(session: Session, user_id: int) -> User | None:
    statement = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    return session.exec(statement).first()


def get_user_by_supabase_id(session: Session, supabase_user_id: str) -> User | None:
    statement = select(User).where(User.supabase_user_id == supabase_user_id, User.deleted_at.is_(None))
    return session.exec(statement).first()


def get_or_create_user_by_supabase_id(
    session: Session,
    *,
    supabase_user_id: str,
    email: str | None = None,
) -> User | None:
    """Resolve a local user from a Supabase Auth UUID.

    Lookup order:
    1. Match by ``supabase_user_id`` (already linked).
    2. Match by ``email`` and link the account (existing user migrating).
    3. Create a new local profile (new Supabase Auth user).

    Returns None only if email is unavailable and no linked user exists.
    """
    # 1. Direct lookup by Supabase UUID
    user = get_user_by_supabase_id(session, supabase_user_id)
    if user is not None:
        return user

    # 2. Match by email and link
    if email:
        user = get_user_by_email(session, email)
        if user is not None:
            user.supabase_user_id = supabase_user_id
            session.add(user)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                # Race condition: another request linked first — re-fetch
                return get_user_by_supabase_id(session, supabase_user_id)
            session.refresh(user)
            return user

    # 3. Auto-create a new local profile
    if not email:
        return None

    user = User(
        email=email.lower().strip(),
        hashed_password="supabase-managed",  # Not used — auth handled by Supabase
        supabase_user_id=supabase_user_id,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        # Email or supabase_user_id collision — re-fetch
        return get_user_by_supabase_id(session, supabase_user_id) or get_user_by_email(session, email)
    session.refresh(user)
    return user


def create_cv(
    session: Session,
    user_id: int,
    filename: str,
    display_name: str,
    raw_text: str,
    clean_text: str,
    summary: str,
    library_summary: str,
    tags: list[str] | None = None,
) -> CV:
    cv = CV(
        user_id=user_id,
        filename=filename,
        display_name=display_name,
        raw_text=raw_text,
        clean_text=clean_text,
        summary=summary,
        library_summary=library_summary,
        is_favorite=False,
        tags=tags or [],
    )
    session.add(cv)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise
    session.refresh(cv)
    return cv


def update_cv_storage_path(session: Session, cv: CV, storage_path: str | None) -> CV:
    cv.storage_path = storage_path
    session.add(cv)
    session.commit()
    session.refresh(cv)
    return cv


def get_cvs_for_user(session: Session, user_id: int, limit: int = 20, offset: int = 0) -> tuple[list[CV], int]:
    """Get paginated CVs for user.
    
    Args:
        session: Database session
        user_id: User ID
        limit: Max items to return (1-200)
        offset: Pagination offset
        
    Returns:
        Tuple of (list of CVs, total count)
    """
    # Clamp limit to reasonable values
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    
    # Get total count
    count_statement = select(func.count()).select_from(CV).where(CV.user_id == user_id, CV.deleted_at.is_(None))
    total = int(session.exec(count_statement).one())
    
    # Get paginated results
    statement = (
        select(CV)
        .options(load_only(*CV_LIST_COLUMNS))
        .where(CV.user_id == user_id, CV.deleted_at.is_(None))
        .order_by(CV.is_favorite.desc(), CV.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    cvs = list(session.exec(statement).all())
    return cvs, total


def get_filtered_cvs_for_user(
    session: Session,
    user_id: int,
    *,
    search: str = "",
    tags: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[CV], int]:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    normalized_search = search.strip().lower()
    normalized_tags = [tag.strip().lower() for tag in (tags or []) if tag.strip()]

    statement = select(CV).options(load_only(*CV_LIST_COLUMNS)).where(CV.user_id == user_id, CV.deleted_at.is_(None))
    count_statement = select(func.count()).select_from(CV).where(CV.user_id == user_id, CV.deleted_at.is_(None))

    if normalized_search:
        search_clause = func.lower(CV.display_name).contains(normalized_search)
        statement = statement.where(search_clause)
        count_statement = count_statement.where(search_clause)

    if normalized_tags and _is_postgres_session(session):
        tag_clause = CV.tags.op("?|")(pg_array(normalized_tags))
        statement = statement.where(tag_clause)
        count_statement = count_statement.where(tag_clause)

    statement = statement.order_by(CV.is_favorite.desc(), CV.created_at.desc())

    if not normalized_tags or _is_postgres_session(session):
        total = int(session.exec(count_statement).one())
        items = list(session.exec(statement.offset(offset).limit(limit)).all())
        return items, total

    candidates = list(session.exec(statement).all())
    filtered = [
        cv for cv in candidates if {tag.lower() for tag in (cv.tags or [])} & set(normalized_tags)
    ]
    total = len(filtered)
    return filtered[offset : offset + limit], total


def get_cv_for_user(session: Session, user_id: int, cv_id: int) -> CV | None:
    statement = select(CV).where(CV.id == cv_id, CV.user_id == user_id, CV.deleted_at.is_(None))
    return session.exec(statement).first()


def get_cv_for_user_by_clean_text(session: Session, user_id: int, clean_text: str) -> CV | None:
    if _is_postgres_session(session):
        clean_text_hash = _sha256_hex(clean_text)
        statement = select(CV).where(
            CV.user_id == user_id,
            _postgres_sha256_expr(CV.clean_text) == clean_text_hash,
            CV.clean_text == clean_text,
            CV.deleted_at.is_(None),
        )
    else:
        statement = select(CV).where(CV.user_id == user_id, CV.clean_text == clean_text, CV.deleted_at.is_(None))
    return session.exec(statement).first()


def delete_cv(session: Session, cv: CV) -> None:
    """Soft-delete a single CV."""
    delete_multiple_cvs(session, [cv])


def get_cvs_for_user_by_ids(session: Session, user_id: int, cv_ids: list[int]) -> list[CV]:
    normalized_ids = [cv_id for cv_id in cv_ids if cv_id > 0]
    if not normalized_ids:
        return []
    statement = select(CV).where(CV.user_id == user_id, CV.id.in_(normalized_ids), CV.deleted_at.is_(None))
    return list(session.exec(statement).all())


def update_cv_tags(session: Session, cv: CV, tags: list[str]) -> CV:
    cv.tags = tags
    session.add(cv)
    session.commit()
    session.refresh(cv)
    return cv


def update_cv_favorite(session: Session, cv: CV, is_favorite: bool) -> CV:
    cv.is_favorite = is_favorite
    session.add(cv)
    session.commit()
    session.refresh(cv)
    return cv


def update_multiple_cv_tags(session: Session, cvs: list[CV], tags: list[str]) -> int:
    updated = 0
    for cv in cvs:
        existing = list(cv.tags or [])
        merged = existing[:]
        for tag in tags:
            if tag not in merged:
                merged.append(tag)
        cv.tags = merged
        session.add(cv)
        updated += 1
    session.commit()
    return updated


def delete_multiple_cvs(session: Session, cvs: list[CV]) -> int:
    """Soft-delete multiple CVs by setting deleted_at."""
    grouped_cv_ids = _group_cv_ids_by_user(cvs)
    if not grouped_cv_ids:
        return 0

    now = datetime.now(timezone.utc)
    try:
        for user_id, cv_ids in grouped_cv_ids.items():
            # Clear cover letter references
            session.exec(
                update(JobAnalysis)
                .where(
                    JobAnalysis.user_id == user_id,
                    JobAnalysis.cover_letter_cv_id.in_(cv_ids),
                )
                .values(
                    cover_letter_cv_id=None,
                    cover_letter_language=None,
                    generated_cover_letter=None,
                )
            )
            # Soft-delete related matches
            session.exec(
                update(CVJobMatch)
                .where(
                    CVJobMatch.user_id == user_id,
                    CVJobMatch.cv_id.in_(cv_ids),
                    CVJobMatch.deleted_at.is_(None),
                )
                .values(deleted_at=now)
            )
            # Soft-delete the CVs
            session.exec(
                update(CV)
                .where(
                    CV.user_id == user_id,
                    CV.id.in_(cv_ids),
                    CV.deleted_at.is_(None),
                )
                .values(deleted_at=now)
            )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise

    storage_service = get_supabase_storage_service()
    for cv in cvs:
        storage_path = getattr(cv, "storage_path", None)
        if not storage_path:
            continue
        try:
            storage_service.delete_cv_pdf(path=storage_path)
        except SupabaseStorageError:
            logger.warning(
                "cv_storage_delete_failed cv_id=%s user_id=%s storage_path=%s",
                cv.id,
                cv.user_id,
                storage_path,
                exc_info=True,
            )

    return sum(len(cv_ids) for cv_ids in grouped_cv_ids.values())


def update_cv_library_summary(session: Session, cv: CV, library_summary: str) -> CV:
    cv.library_summary = library_summary
    session.add(cv)
    session.commit()
    session.refresh(cv)
    return cv


def create_job_analysis(
    session: Session,
    user_id: int,
    title: str,
    company: str,
    description: str,
    clean_description: str,
    analysis_result: dict,
) -> JobAnalysis:
    job = JobAnalysis(
        user_id=user_id,
        title=title,
        company=company,
        description=description,
        clean_description=clean_description,
        analysis_result=analysis_result,
        is_saved=False,
    )
    session.add(job)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise
    session.refresh(job)
    return job


def get_matching_job_analysis(
    session: Session,
    user_id: int,
    title: str,
    company: str,
    clean_description: str,
) -> JobAnalysis | None:
    # Check for identical analysis to avoid re-running slow LLM calls
    if _is_postgres_session(session):
        clean_description_hash = _sha256_hex(clean_description)
        statement = select(JobAnalysis).where(
            JobAnalysis.user_id == user_id,
            JobAnalysis.title == title,
            JobAnalysis.company == company,
            _postgres_sha256_expr(JobAnalysis.clean_description) == clean_description_hash,
            JobAnalysis.clean_description == clean_description,
            JobAnalysis.deleted_at.is_(None),
        )
    else:
        statement = select(JobAnalysis).where(
            JobAnalysis.user_id == user_id,
            JobAnalysis.title == title,
            JobAnalysis.company == company,
            JobAnalysis.clean_description == clean_description,
            JobAnalysis.deleted_at.is_(None),
        )
    return session.exec(statement).first()


def get_jobs_for_user(
    session: Session,
    user_id: int,
    *,
    limit: int = 20,
    offset: int = 0,
    is_saved: bool | None = None,
) -> tuple[list[JobAnalysis], int]:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    count_statement = select(func.count()).select_from(JobAnalysis).where(JobAnalysis.user_id == user_id, JobAnalysis.deleted_at.is_(None))
    statement = select(JobAnalysis).options(load_only(*JOB_LIST_COLUMNS)).where(JobAnalysis.user_id == user_id, JobAnalysis.deleted_at.is_(None))
    if is_saved is not None:
        count_statement = count_statement.where(JobAnalysis.is_saved == is_saved)
        statement = statement.where(JobAnalysis.is_saved == is_saved)
    total = int(session.exec(count_statement).one())
    statement = statement.order_by(JobAnalysis.is_saved.desc(), JobAnalysis.created_at.desc()).offset(offset).limit(limit)
    return list(session.exec(statement).all()), total


def get_job_for_user(session: Session, user_id: int, job_id: int) -> JobAnalysis | None:
    statement = select(JobAnalysis).where(JobAnalysis.id == job_id, JobAnalysis.user_id == user_id, JobAnalysis.deleted_at.is_(None))
    return session.exec(statement).first()


def get_job_by_id(session: Session, job_id: int) -> JobAnalysis | None:
    statement = select(JobAnalysis).where(JobAnalysis.id == job_id, JobAnalysis.deleted_at.is_(None))
    return session.exec(statement).first()


def delete_job(session: Session, job: JobAnalysis) -> None:
    """Soft-delete a job and its dependent matches."""
    now = datetime.now(timezone.utc)
    try:
        # Soft-delete dependent matches
        session.exec(
            update(CVJobMatch)
            .where(CVJobMatch.job_id == job.id, CVJobMatch.user_id == job.user_id, CVJobMatch.deleted_at.is_(None))
            .values(deleted_at=now)
        )
        # Soft-delete the job
        job.deleted_at = now
        session.add(job)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise


def update_job_status(
    session: Session,
    job: JobAnalysis,
    status: str,
    applied_date,
) -> JobAnalysis:
    job.status = status
    if applied_date is not None:
        if applied_date.tzinfo is None:
            applied_date = applied_date.replace(tzinfo=timezone.utc)
        else:
            applied_date = applied_date.astimezone(timezone.utc)
        job.applied_date = applied_date
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def update_job_notes(session: Session, job: JobAnalysis, notes: str | None) -> JobAnalysis:
    job.notes = notes
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def update_job_saved(session: Session, job: JobAnalysis, is_saved: bool) -> JobAnalysis:
    job.is_saved = is_saved
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def update_job_analysis_result(session: Session, job: JobAnalysis, analysis_result: dict) -> JobAnalysis:
    job.analysis_result = analysis_result
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def get_cached_cover_letter(
    session: Session,
    user_id: int,
    job_id: int,
    cv_id: int,
    language: str,
) -> str | None:
    job = get_job_for_user(session, user_id, job_id)
    if job is None:
        return None

    if (
        getattr(job, "cover_letter_cv_id", None) == cv_id
        and getattr(job, "cover_letter_language", None) == language
        and isinstance(getattr(job, "generated_cover_letter", None), str)
        and job.generated_cover_letter.strip()
    ):
        return job.generated_cover_letter

    return None


def update_job_cover_letter(
    session: Session,
    job: JobAnalysis,
    cv_id: int,
    language: str,
    cover_letter: str,
) -> JobAnalysis:
    job.cover_letter_cv_id = cv_id
    job.cover_letter_language = language
    job.generated_cover_letter = cover_letter
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def create_match(
    session: Session,
    user_id: int,
    cv_id: int,
    job_id: int,
    fit_level: str,
    fit_summary: str,
    strengths: list[str],
    missing_skills: list[str],
    recommended: bool = False,
) -> CVJobMatch:
    match = CVJobMatch(
        user_id=user_id,
        cv_id=cv_id,
        job_id=job_id,
        fit_level=fit_level,
        fit_summary=fit_summary,
        strengths=strengths,
        missing_skills=missing_skills,
        recommended=recommended,
    )
    session.add(match)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        existing = get_match_for_user_by_cv_and_job(session, user_id, cv_id, job_id)
        if existing is not None:
            return existing
        raise exc
    session.refresh(match)
    return match


def update_match_analysis(
    session: Session,
    match: CVJobMatch,
    fit_level: str,
    fit_summary: str,
    strengths: list[str],
    missing_skills: list[str],
) -> CVJobMatch:
    match.fit_level = fit_level
    match.fit_summary = fit_summary
    match.strengths = strengths
    match.missing_skills = missing_skills
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def clear_recommendations_for_job(session: Session, user_id: int, job_id: int) -> None:
    # Toggle off recommended flag before setting a new winner
    session.exec(
        update(CVJobMatch)
        .where(CVJobMatch.user_id == user_id, CVJobMatch.job_id == job_id, CVJobMatch.deleted_at.is_(None))
        .values(recommended=False)
    )
    session.commit()


def set_recommended_match(session: Session, match: CVJobMatch) -> CVJobMatch:
    match.recommended = True
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def replace_recommended_match(session: Session, match: CVJobMatch) -> CVJobMatch:
    session.exec(
        update(CVJobMatch)
        .where(
            CVJobMatch.user_id == match.user_id,
            CVJobMatch.job_id == match.job_id,
            CVJobMatch.deleted_at.is_(None),
        )
        .values(recommended=False)
    )
    session.exec(
        update(CVJobMatch)
        .where(
            CVJobMatch.id == match.id,
            CVJobMatch.user_id == match.user_id,
            CVJobMatch.job_id == match.job_id,
            CVJobMatch.deleted_at.is_(None),
        )
        .values(recommended=True)
    )
    session.commit()
    session.refresh(match)
    return match


def get_match_for_user_by_cv_and_job(session: Session, user_id: int, cv_id: int, job_id: int) -> CVJobMatch | None:
    statement = select(CVJobMatch).where(
        CVJobMatch.user_id == user_id,
        CVJobMatch.cv_id == cv_id,
        CVJobMatch.job_id == job_id,
        CVJobMatch.deleted_at.is_(None),
    )
    return session.exec(statement).first()


def get_matches_for_user(
    session: Session,
    user_id: int,
    *,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[CVJobMatch], int]:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    count_statement = select(func.count()).select_from(CVJobMatch).where(CVJobMatch.user_id == user_id, CVJobMatch.deleted_at.is_(None))
    total = int(session.exec(count_statement).one())
    statement = (
        select(CVJobMatch)
        .where(CVJobMatch.user_id == user_id, CVJobMatch.deleted_at.is_(None))
        .order_by(CVJobMatch.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(statement).all()), total


def get_match_for_user(session: Session, user_id: int, match_id: int) -> CVJobMatch | None:
    statement = select(CVJobMatch).where(CVJobMatch.user_id == user_id, CVJobMatch.id == match_id, CVJobMatch.deleted_at.is_(None))
    return session.exec(statement).first()


def get_matches_for_job(session: Session, user_id: int, job_id: int) -> list[CVJobMatch]:
    statement = select(CVJobMatch).where(
        CVJobMatch.user_id == user_id,
        CVJobMatch.job_id == job_id,
        CVJobMatch.deleted_at.is_(None),
    )
    return list(session.exec(statement).all())
