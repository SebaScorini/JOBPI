from sqlmodel import Session, select

from app.db.models import CVJobMatch, JobAnalysis, StoredCV


def create_cv(session: Session, name: str, file_hash: str, cleaned_text: str) -> StoredCV:
    cv = StoredCV(name=name, file_hash=file_hash, cleaned_text=cleaned_text)
    session.add(cv)
    session.commit()
    session.refresh(cv)
    return cv


def get_cv_by_hash(session: Session, file_hash: str) -> StoredCV | None:
    statement = select(StoredCV).where(StoredCV.file_hash == file_hash)
    return session.exec(statement).first()


def get_all_cvs(session: Session) -> list[StoredCV]:
    statement = select(StoredCV).order_by(StoredCV.created_at.desc())
    return list(session.exec(statement).all())


def get_cv(session: Session, cv_id: int) -> StoredCV | None:
    return session.get(StoredCV, cv_id)


def delete_cv(session: Session, cv: StoredCV) -> None:
    statement = select(CVJobMatch).where(CVJobMatch.cv_id == cv.id)
    matches = session.exec(statement).all()
    for match in matches:
        session.delete(match)
    session.delete(cv)
    session.commit()


def create_job_analysis(
    session: Session,
    job_hash: str,
    title: str,
    company: str,
    cleaned_description: str,
    result_json: str,
) -> JobAnalysis:
    job = JobAnalysis(
        job_hash=job_hash,
        title=title,
        company=company,
        cleaned_description=cleaned_description,
        result_json=result_json,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def get_job_by_hash(session: Session, job_hash: str) -> JobAnalysis | None:
    statement = select(JobAnalysis).where(JobAnalysis.job_hash == job_hash)
    return session.exec(statement).first()


def get_job(session: Session, job_id: int) -> JobAnalysis | None:
    return session.get(JobAnalysis, job_id)


def create_match(
    session: Session,
    cv_id: int,
    job_id: int,
    result_json: str,
    heuristic_score: float,
) -> CVJobMatch:
    match = CVJobMatch(
        cv_id=cv_id,
        job_id=job_id,
        result_json=result_json,
        heuristic_score=heuristic_score,
    )
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def get_match(session: Session, cv_id: int, job_id: int) -> CVJobMatch | None:
    statement = select(CVJobMatch).where(
        CVJobMatch.cv_id == cv_id,
        CVJobMatch.job_id == job_id,
    )
    return session.exec(statement).first()


def get_all_matches_for_job(session: Session, job_id: int) -> list[CVJobMatch]:
    statement = select(CVJobMatch).where(CVJobMatch.job_id == job_id)
    return list(session.exec(statement).all())
