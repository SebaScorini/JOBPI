import unittest
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlmodel import SQLModel, Session, create_engine

from app.db import crud
from app.services.job_analyzer import JobAnalyzerService


class JobDeleteServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        tests_tmp_dir = Path.cwd() / ".tmp-tests"
        tests_tmp_dir.mkdir(exist_ok=True)
        self.database_path = tests_tmp_dir / f"job-delete-test-{uuid4().hex}.db"
        if self.database_path.exists():
            self.database_path.unlink()
        self.engine = create_engine(f"sqlite:///{self.database_path.resolve().as_posix()}")
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.service = JobAnalyzerService()
        self.owner = crud.create_user(self.session, "owner@example.com", "hashed-password")
        self.other_user = crud.create_user(self.session, "other@example.com", "hashed-password")

    def tearDown(self) -> None:
        self.service._executor.shutdown(wait=False, cancel_futures=True)
        self.session.close()
        self.engine.dispose()
        if self.database_path.exists():
            self.database_path.unlink()

    def _create_job(self, user_id: int):
        return crud.create_job_analysis(
            self.session,
            user_id=user_id,
            title="Senior Backend Engineer",
            company="ACME",
            description="A" * 60,
            clean_description="A" * 60,
            analysis_result={
                "summary": "summary",
                "seniority": "senior",
                "role_type": "backend",
                "required_skills": [],
                "nice_to_have_skills": [],
                "responsibilities": [],
                "how_to_prepare": [],
                "learning_path": [],
                "missing_skills": [],
                "resume_tips": [],
                "interview_tips": [],
                "portfolio_project_ideas": [],
                "_language": "english",
            },
        )

    def test_delete_job_returns_404_when_job_does_not_exist(self):
        with self.assertRaises(HTTPException) as exc_info:
            self.service.delete_job(self.session, self.owner, 999999)

        self.assertEqual(exc_info.exception.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_job_returns_403_when_job_belongs_to_another_user(self):
        job = self._create_job(self.other_user.id)

        with self.assertRaises(HTTPException) as exc_info:
            self.service.delete_job(self.session, self.owner, job.id)

        self.assertEqual(exc_info.exception.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIsNotNone(crud.get_job_by_id(self.session, job.id))

    def test_delete_job_removes_owned_job_and_returns_success(self):
        job = self._create_job(self.owner.id)

        result = self.service.delete_job(self.session, self.owner, job.id)

        self.assertTrue(result.success)
        self.assertIsNone(crud.get_job_by_id(self.session, job.id))


if __name__ == "__main__":
    unittest.main()
