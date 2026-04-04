from datetime import timezone

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from app.models import CV, CVJobMatch, JobAnalysis, User


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
    statement = select(User).where(User.email == email.lower().strip())
    return session.exec(statement).first()


def get_user_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


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
    count_statement = select(func.count()).select_from(CV).where(CV.user_id == user_id)
    total = int(session.exec(count_statement).one())
    
    # Get paginated results
    statement = select(CV).where(CV.user_id == user_id).order_by(CV.created_at.desc()).offset(offset).limit(limit)
    cvs = list(session.exec(statement).all())
    return cvs, total


def get_cv_for_user(session: Session, user_id: int, cv_id: int) -> CV | None:
    statement = select(CV).where(CV.id == cv_id, CV.user_id == user_id)
    return session.exec(statement).first()


def get_cv_for_user_by_clean_text(session: Session, user_id: int, clean_text: str) -> CV | None:
    statement = select(CV).where(CV.user_id == user_id, CV.clean_text == clean_text)
    return session.exec(statement).first()


def delete_cv(session: Session, cv: CV) -> None:
    cover_letter_jobs = session.exec(
        select(JobAnalysis).where(
            JobAnalysis.user_id == cv.user_id,
            JobAnalysis.cover_letter_cv_id == cv.id,
        )
    ).all()
    for job in cover_letter_jobs:
        job.cover_letter_cv_id = None
        job.cover_letter_language = None
        job.generated_cover_letter = None
        session.add(job)

    statement = select(CVJobMatch).where(CVJobMatch.cv_id == cv.id, CVJobMatch.user_id == cv.user_id)
    matches = session.exec(statement).all()
    for match in matches:
        session.delete(match)
    session.delete(cv)
    session.commit()


def update_cv_tags(session: Session, cv: CV, tags: list[str]) -> CV:
    cv.tags = tags
    session.add(cv)
    session.commit()
    session.refresh(cv)
    return cv


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
    statement = select(JobAnalysis).where(
        JobAnalysis.user_id == user_id,
        JobAnalysis.title == title,
        JobAnalysis.company == company,
        JobAnalysis.clean_description == clean_description,
    )
    return session.exec(statement).first()


def get_jobs_for_user(session: Session, user_id: int) -> list[JobAnalysis]:
    statement = select(JobAnalysis).where(JobAnalysis.user_id == user_id).order_by(JobAnalysis.created_at.desc())
    return list(session.exec(statement).all())


def get_job_for_user(session: Session, user_id: int, job_id: int) -> JobAnalysis | None:
    statement = select(JobAnalysis).where(JobAnalysis.id == job_id, JobAnalysis.user_id == user_id)
    return session.exec(statement).first()


def get_job_by_id(session: Session, job_id: int) -> JobAnalysis | None:
    return session.get(JobAnalysis, job_id)


def delete_job(session: Session, job: JobAnalysis) -> None:
    # Remove dependent matches first so the job delete stays valid across DB backends.
    statement = select(CVJobMatch).where(CVJobMatch.job_id == job.id, CVJobMatch.user_id == job.user_id)
    matches = session.exec(statement).all()
    try:
        for match in matches:
            session.delete(match)
        session.delete(job)
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
        job.cover_letter_cv_id == cv_id
        and job.cover_letter_language == language
        and isinstance(job.generated_cover_letter, str)
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
    statement = select(CVJobMatch).where(CVJobMatch.user_id == user_id, CVJobMatch.job_id == job_id)
    for match in session.exec(statement).all():
        match.recommended = False
        session.add(match)
    session.commit()


def set_recommended_match(session: Session, match: CVJobMatch) -> CVJobMatch:
    match.recommended = True
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def get_match_for_user_by_cv_and_job(session: Session, user_id: int, cv_id: int, job_id: int) -> CVJobMatch | None:
    statement = select(CVJobMatch).where(
        CVJobMatch.user_id == user_id,
        CVJobMatch.cv_id == cv_id,
        CVJobMatch.job_id == job_id,
    )
    return session.exec(statement).first()


def get_matches_for_user(session: Session, user_id: int) -> list[CVJobMatch]:
    statement = select(CVJobMatch).where(CVJobMatch.user_id == user_id).order_by(CVJobMatch.created_at.desc())
    return list(session.exec(statement).all())


def get_match_for_user(session: Session, user_id: int, match_id: int) -> CVJobMatch | None:
    statement = select(CVJobMatch).where(CVJobMatch.user_id == user_id, CVJobMatch.id == match_id)
    return session.exec(statement).first()


def get_matches_for_job(session: Session, user_id: int, job_id: int) -> list[CVJobMatch]:
    statement = select(CVJobMatch).where(
        CVJobMatch.user_id == user_id,
        CVJobMatch.job_id == job_id,
    )
    return list(session.exec(statement).all())
