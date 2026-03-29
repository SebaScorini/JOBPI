from sqlmodel import Session, select

from app.models import CV, CVJobMatch, JobAnalysis, User


def create_user(session: Session, email: str, hashed_password: str) -> User:
    user = User(email=email.lower().strip(), hashed_password=hashed_password)
    session.add(user)
    session.commit()
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
) -> CV:
    cv = CV(
        user_id=user_id,
        filename=filename,
        display_name=display_name,
        raw_text=raw_text,
        clean_text=clean_text,
        summary=summary,
    )
    session.add(cv)
    session.commit()
    session.refresh(cv)
    return cv


def get_cvs_for_user(session: Session, user_id: int) -> list[CV]:
    # Enforce user ownership during retrieval
    statement = select(CV).where(CV.user_id == user_id).order_by(CV.created_at.desc())
    return list(session.exec(statement).all())


def get_cv_for_user(session: Session, user_id: int, cv_id: int) -> CV | None:
    statement = select(CV).where(CV.id == cv_id, CV.user_id == user_id)
    return session.exec(statement).first()


def delete_cv(session: Session, cv: CV) -> None:
    statement = select(CVJobMatch).where(CVJobMatch.cv_id == cv.id, CVJobMatch.user_id == cv.user_id)
    matches = session.exec(statement).all()
    for match in matches:
        session.delete(match)
    session.delete(cv)
    session.commit()


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
    session.commit()
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


def update_job_status(
    session: Session,
    job: JobAnalysis,
    status: str,
    applied_date,
) -> JobAnalysis:
    job.status = status
    if applied_date is not None:
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
