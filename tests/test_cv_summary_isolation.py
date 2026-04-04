import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from sqlmodel import SQLModel, Session, create_engine

from app.db import crud
from app.services.cv_library_service import CvLibraryService
from app.services.cv_library_summary_service import CvLibrarySummaryService, _normalize_library_summary


class _LeakySummaryModule:
    def __init__(self) -> None:
        self._first_result = None

    def __call__(self, *, cv: str, max_tokens: int | None = None):
        if self._first_result is None:
            headline = cv.splitlines()[0].strip()
            self._first_result = SimpleNamespace(summary=f"{headline} summary")
        return self._first_result


def _call_summary_generator(**kwargs):
    return kwargs["callable_"](cv=kwargs["cv"], max_tokens=kwargs["max_tokens"])


class CvLibrarySummaryIsolationTests(unittest.TestCase):
    def test_generate_uses_fresh_generator_for_each_cv(self):
        service = CvLibrarySummaryService()

        with (
            patch("app.services.cv_library_summary_service.configure_dspy", return_value=None),
            patch("app.services.cv_library_summary_service.CvLibrarySummaryModule", _LeakySummaryModule),
            patch("app.services.cv_library_summary_service.run_ai_call_with_timeout", side_effect=_call_summary_generator),
        ):
            first_summary = service.generate("Python FastAPI engineer\nBuilt backend services")
            second_summary = service.generate("React TypeScript engineer\nBuilt frontend interfaces")

        service._executor.shutdown(wait=False, cancel_futures=True)

        self.assertNotEqual(first_summary, second_summary)
        self.assertIn("python", first_summary.lower())
        self.assertIn("react", second_summary.lower())


class CvLibraryPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        tests_tmp_dir = Path.cwd() / ".tmp-tests"
        tests_tmp_dir.mkdir(exist_ok=True)
        self.database_path = tests_tmp_dir / f"cv-summary-test-{uuid4().hex}.db"
        if self.database_path.exists():
            self.database_path.unlink()
        self.engine = create_engine(f"sqlite:///{self.database_path.resolve().as_posix()}")
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.user = crud.create_user(self.session, "tester@example.com", "hashed-password")

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()
        if self.database_path.exists():
            self.database_path.unlink()

    def test_upload_cv_persists_unique_clean_text_and_summary_per_record(self):
        service = CvLibraryService()
        settings = SimpleNamespace(
            should_bypass_user_limits=lambda email: True,
            max_cv_text_chars=8000,
        )

        with (
            patch("app.services.cv_library_service.get_settings", return_value=settings),
            patch(
                "app.services.cv_library_service.extract_raw_pdf_text",
                side_effect=[
                    "Raw CV one",
                    "Raw CV two",
                ],
            ),
            patch(
                "app.services.cv_library_service.preprocess_cv_text",
                side_effect=[
                    "Python FastAPI experience",
                    "React TypeScript experience",
                ],
            ),
            patch.object(
                CvLibraryService,
                "_build_library_summary",
                side_effect=[
                    "Python backend summary.",
                    "React frontend summary.",
                ],
            ),
        ):
            first_cv = service.upload_cv(
                session=self.session,
                user=self.user,
                display_name="Backend CV",
                filename="backend.pdf",
                file_bytes=b"%PDF-1.4 backend",
            )
            second_cv = service.upload_cv(
                session=self.session,
                user=self.user,
                display_name="Frontend CV",
                filename="frontend.pdf",
                file_bytes=b"%PDF-1.4 frontend",
            )

        stored_cvs, total = crud.get_cvs_for_user(self.session, self.user.id)
        stored_by_id = {cv.id: cv for cv in stored_cvs}

        self.assertNotEqual(first_cv.id, second_cv.id)
        self.assertEqual(total, 2)
        self.assertEqual(stored_by_id[first_cv.id].clean_text, "Python FastAPI experience")
        self.assertEqual(stored_by_id[second_cv.id].clean_text, "React TypeScript experience")
        self.assertEqual(stored_by_id[first_cv.id].library_summary, "Python backend summary.")
        self.assertEqual(stored_by_id[second_cv.id].library_summary, "React frontend summary.")
        self.assertNotEqual(
            stored_by_id[first_cv.id].library_summary,
            stored_by_id[second_cv.id].library_summary,
        )


class CvLibrarySummaryNormalizationTests(unittest.TestCase):
    def test_normalize_library_summary_strips_model_completion_artifacts(self):
        normalized = _normalize_library_summary(
            "Backend developer with Python and FastAPI experience. [[ ## completed ]]"
        )

        self.assertEqual(
            normalized,
            "Backend developer with Python and FastAPI experience.",
        )


if __name__ == "__main__":
    unittest.main()
