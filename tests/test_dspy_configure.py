import threading
import unittest
from unittest.mock import patch
from types import SimpleNamespace

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
            dspy_temperature=0.35,
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

    def test_normalize_dspy_model_prefixes_openrouter_when_missing(self):
        normalized = app_settings.normalize_dspy_model(
            "nvidia/nemotron-3-super-120b-a12b:free",
            "https://openrouter.ai/api/v1",
        )

        self.assertEqual(normalized, "openrouter/nvidia/nemotron-3-super-120b-a12b:free")

    def test_configure_dspy_normalizes_openrouter_model_before_initializing_lm(self):
        configured_lms: list[object] = []
        fake_lm = object()
        fake_settings = SimpleNamespace(
            openrouter_api_key="test-key",
            dspy_model="nvidia/nemotron-3-super-120b-a12b:free",
            openrouter_base_url="https://openrouter.ai/api/v1",
            dspy_temperature=0.35,
            max_output_tokens=512,
        )

        with (
            patch("app.core.settings.get_settings", return_value=fake_settings),
            patch("app.core.settings.dspy.LM", return_value=fake_lm) as lm_ctor,
            patch(
                "app.core.settings.dspy.settings",
                new=SimpleNamespace(configure=lambda **kwargs: configured_lms.append(kwargs["lm"])),
            ),
        ):
            result = app_settings.configure_dspy()

        self.assertIs(result, fake_lm)
        self.assertEqual(configured_lms, [fake_lm])
        self.assertEqual(
            lm_ctor.call_args.kwargs["model"],
            "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
        )

    def test_settings_accepts_groq_api_key_and_base_url_fallback(self):
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "OPENROUTER_API_KEY": "",
                "OPENROUTER_BASE_URL": "",
                "GROQ_API_KEY": "groq-test-key",
                "GROQ_BASE_URL": "",
                "OPENAI_API_KEY": "",
                "OPENAI_BASE_URL": "",
            },
            clear=True,
        ):
            settings = app_settings.Settings()

        self.assertEqual(settings.openrouter_api_key, "groq-test-key")
        self.assertEqual(settings.openrouter_base_url, "https://api.groq.com/openai/v1")

    def test_settings_prefers_openrouter_over_groq_when_both_are_defined(self):
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "OPENROUTER_API_KEY": "openrouter-test-key",
                "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
                "GROQ_API_KEY": "groq-test-key",
                "GROQ_BASE_URL": "https://api.groq.com/openai/v1",
                "OPENAI_API_KEY": "",
                "OPENAI_BASE_URL": "",
            },
            clear=True,
        ):
            settings = app_settings.Settings()

        self.assertEqual(settings.openrouter_api_key, "openrouter-test-key")
        self.assertEqual(settings.openrouter_base_url, "https://openrouter.ai/api/v1")

    def test_build_dspy_lm_kwargs_defaults_to_omit_reasoning_for_openrouter(self):
        kwargs = app_settings.build_dspy_lm_kwargs(api_base="https://openrouter.ai/api/v1")

        self.assertEqual(kwargs, {})

    def test_build_dspy_lm_kwargs_includes_reasoning_when_explicitly_enabled(self):
        with patch.dict("os.environ", {"DSPY_SEND_REASONING_EXTRA_BODY": "true"}, clear=False):
            kwargs = app_settings.build_dspy_lm_kwargs(api_base="https://openrouter.ai/api/v1")

        self.assertEqual(kwargs, {"extra_body": {"reasoning": {"enabled": False}}})

    def test_build_dspy_lm_kwargs_omits_reasoning_for_openai_compatible_base(self):
        kwargs = app_settings.build_dspy_lm_kwargs(api_base="https://api.openai.com/v1")

        self.assertEqual(kwargs, {})


if __name__ == "__main__":
    unittest.main()
