import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.core import settings as app_settings


class ConfigureDspyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_lm = app_settings._DSPY_LM
        app_settings._DSPY_LM = None

    def tearDown(self) -> None:
        app_settings._DSPY_LM = self._original_lm

    def test_configure_dspy_reuses_cached_lm_across_threads(self):
        configured_lms: list[object] = []
        fake_lm = object()
        fake_settings = SimpleNamespace(
            openrouter_api_key="test-key",
            dspy_model="openrouter/test-model",
            openrouter_base_url="https://openrouter.ai/api/v1",
            dspy_temperature=0.2,
            max_output_tokens=512,
        )
        thread_results: list[object] = []
        thread_errors: list[BaseException] = []

        def run_in_thread() -> None:
            try:
                thread_results.append(app_settings.configure_dspy())
            except BaseException as exc:
                thread_errors.append(exc)

        with (
            patch("app.core.settings.get_settings", return_value=fake_settings),
            patch("app.core.settings.dspy.LM", return_value=fake_lm),
            patch(
                "app.core.settings.dspy.settings",
                new=SimpleNamespace(configure=lambda **kwargs: configured_lms.append(kwargs["lm"])),
            ),
        ):
            first_result = app_settings.configure_dspy()
            worker = threading.Thread(target=run_in_thread)
            worker.start()
            worker.join(timeout=5)

        self.assertFalse(thread_errors)
        self.assertIs(first_result, fake_lm)
        self.assertEqual(thread_results, [fake_lm])
        self.assertEqual(configured_lms, [fake_lm])


if __name__ == "__main__":
    unittest.main()
