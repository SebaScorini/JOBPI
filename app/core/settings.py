import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import dspy
from dotenv import load_dotenv
from pydantic import BaseModel, Field


AppEnv = Literal["development", "production"]

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", override=False)

ENV_DEFAULTS: dict[AppEnv, dict[str, object]] = {
    "development": {
        "rate_limit_enabled": False,
        "auth_window_seconds": 300,
        "auth_register_limit": 20,
        "auth_login_limit": 30,
        "job_analyze_window_seconds": 300,
        "job_analyze_limit": 30,
        "match_cvs_window_seconds": 300,
        "match_cvs_limit": 30,
        "cover_letter_window_seconds": 300,
        "cover_letter_limit": 15,
        "cv_upload_window_seconds": 300,
        "cv_upload_limit": 20,
        "max_pdf_size_mb": 5,
        "max_cvs_per_upload": 10,
        "max_job_description_chars": 12000,
        "max_cv_text_chars": 8000,
        "max_output_tokens": 540,
        "job_analysis_max_tokens": 945,
        "job_analysis_retry_max_tokens": 608,
        "job_preprocess_target_chars": 5000,
        "ai_timeout_seconds": 45,
    },
    "production": {
        "rate_limit_enabled": True,
        "auth_window_seconds": 600,
        "auth_register_limit": 3,
        "auth_login_limit": 5,
        "job_analyze_window_seconds": 3600,
        "job_analyze_limit": 6,
        "match_cvs_window_seconds": 3600,
        "match_cvs_limit": 8,
        "cover_letter_window_seconds": 3600,
        "cover_letter_limit": 4,
        "cv_upload_window_seconds": 3600,
        "cv_upload_limit": 5,
        "max_pdf_size_mb": 2,
        "max_cvs_per_upload": 3,
        "max_job_description_chars": 2500,
        "max_cv_text_chars": 4000,
        "max_output_tokens": 540,
        "job_analysis_max_tokens": 878,
        "job_analysis_retry_max_tokens": 540,
        "job_preprocess_target_chars": 3500,
        "ai_timeout_seconds": 20,
    },
}


def _get_env_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _get_app_env() -> AppEnv:
    value = _get_env_str("APP_ENV", "development").lower()
    if value in {"development", "production"}:
        return value  # type: ignore[return-value]
    return "development"


def _env_default(key: str) -> object:
    return ENV_DEFAULTS[_get_app_env()][key]


def _get_env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _get_env_int(name: str, default: int) -> int:
    value = _get_env_str(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_env_float(name: str, default: float) -> float:
    value = _get_env_str(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _parse_csv_setting(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _default_sqlite_database_url() -> str:
    return f"sqlite:///{(BASE_DIR / 'jobpi.db').as_posix()}"


def _default_database_url() -> str:
    # Keep a zero-config local path for development only.
    if _get_app_env() == "development":
        return _default_sqlite_database_url()
    return ""


class Settings(BaseModel):
    app_env: AppEnv = Field(default_factory=_get_app_env)
    openrouter_api_key: str = Field(default_factory=lambda: _get_env_str("OPENROUTER_API_KEY"))
    openrouter_base_url: str = Field(
        default_factory=lambda: _get_env_str("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    )
    database_url: str = Field(default_factory=lambda: _get_env_str("DATABASE_URL", _default_database_url()))
    secret_key: str = Field(
        default_factory=lambda: _get_env_str(
            "SECRET_KEY",
            _get_env_str("JWT_SECRET_KEY", "dev-only-secret-key-change-me"),
        )
    )
    access_token_expire_minutes: int = Field(
        default_factory=lambda: _get_env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 60)
    )
    dspy_model: str = Field(
        default_factory=lambda: _get_env_str("DSPY_MODEL", "openrouter/minimax/minimax-m2.5:free")
    )
    dspy_temperature: float = Field(default_factory=lambda: _get_env_float("DSPY_TEMPERATURE", 0.0))
    rate_limit_enabled: bool = Field(
        default_factory=lambda: _get_env_bool("RATE_LIMIT_ENABLED", bool(_env_default("rate_limit_enabled")))
    )
    trusted_user_email: str = Field(default_factory=lambda: _get_env_str("TRUSTED_USER_EMAIL"))
    auth_window_seconds: int = Field(
        default_factory=lambda: _get_env_int("AUTH_RATE_LIMIT_WINDOW_SECONDS", int(_env_default("auth_window_seconds")))
    )
    auth_register_limit: int = Field(
        default_factory=lambda: _get_env_int("AUTH_REGISTER_RATE_LIMIT", int(_env_default("auth_register_limit")))
    )
    auth_login_limit: int = Field(
        default_factory=lambda: _get_env_int("AUTH_LOGIN_RATE_LIMIT", int(_env_default("auth_login_limit")))
    )
    job_analyze_window_seconds: int = Field(
        default_factory=lambda: _get_env_int(
            "JOB_ANALYZE_RATE_LIMIT_WINDOW_SECONDS",
            int(_env_default("job_analyze_window_seconds")),
        )
    )
    job_analyze_limit: int = Field(
        default_factory=lambda: _get_env_int("JOB_ANALYZE_RATE_LIMIT", int(_env_default("job_analyze_limit")))
    )
    match_cvs_window_seconds: int = Field(
        default_factory=lambda: _get_env_int(
            "MATCH_CVS_RATE_LIMIT_WINDOW_SECONDS",
            int(_env_default("match_cvs_window_seconds")),
        )
    )
    match_cvs_limit: int = Field(
        default_factory=lambda: _get_env_int("MATCH_CVS_RATE_LIMIT", int(_env_default("match_cvs_limit")))
    )
    cover_letter_window_seconds: int = Field(
        default_factory=lambda: _get_env_int(
            "COVER_LETTER_RATE_LIMIT_WINDOW_SECONDS",
            int(_env_default("cover_letter_window_seconds")),
        )
    )
    cover_letter_limit: int = Field(
        default_factory=lambda: _get_env_int("COVER_LETTER_RATE_LIMIT", int(_env_default("cover_letter_limit")))
    )
    cv_upload_window_seconds: int = Field(
        default_factory=lambda: _get_env_int(
            "CV_UPLOAD_RATE_LIMIT_WINDOW_SECONDS",
            int(_env_default("cv_upload_window_seconds")),
        )
    )
    cv_upload_limit: int = Field(
        default_factory=lambda: _get_env_int("CV_UPLOAD_RATE_LIMIT", int(_env_default("cv_upload_limit")))
    )
    max_pdf_size_mb: int = Field(
        default_factory=lambda: _get_env_int("MAX_PDF_SIZE_MB", int(_env_default("max_pdf_size_mb")))
    )
    max_cvs_per_upload: int = Field(
        default_factory=lambda: _get_env_int("MAX_CVS_PER_UPLOAD", int(_env_default("max_cvs_per_upload")))
    )
    max_job_description_chars: int = Field(
        default_factory=lambda: _get_env_int(
            "MAX_JOB_DESCRIPTION_CHARS", int(_env_default("max_job_description_chars"))
        )
    )
    max_cv_text_chars: int = Field(
        default_factory=lambda: _get_env_int("MAX_CV_TEXT_CHARS", int(_env_default("max_cv_text_chars")))
    )
    max_output_tokens: int = Field(
        default_factory=lambda: _get_env_int(
            "MAX_OUTPUT_TOKENS",
            _get_env_int("DSPY_MAX_TOKENS", int(_env_default("max_output_tokens"))),
        )
    )
    job_analysis_max_tokens: int = Field(
        default_factory=lambda: _get_env_int(
            "JOB_ANALYSIS_MAX_TOKENS",
            int(_env_default("job_analysis_max_tokens")),
        )
    )
    job_analysis_retry_max_tokens: int = Field(
        default_factory=lambda: _get_env_int(
            "JOB_ANALYSIS_RETRY_MAX_TOKENS",
            int(_env_default("job_analysis_retry_max_tokens")),
        )
    )
    job_preprocess_target_chars: int = Field(
        default_factory=lambda: _get_env_int(
            "JOB_PREPROCESS_TARGET_CHARS",
            int(_env_default("job_preprocess_target_chars")),
        )
    )
    ai_timeout_seconds: int = Field(
        default_factory=lambda: _get_env_int(
            "AI_TIMEOUT_SECONDS",
            _get_env_int("DSPY_TIMEOUT_SECONDS", int(_env_default("ai_timeout_seconds"))),
        )
    )
    sqlite_timeout_seconds: int = Field(
        default_factory=lambda: _get_env_int("SQLITE_TIMEOUT_SECONDS", 30)
    )
    frontend_url: str = Field(default_factory=lambda: _get_env_str("FRONTEND_URL"))
    cors_origins: list[str] = Field(
        default_factory=lambda: _parse_csv_setting(
            _get_env_str(
                "CORS_ORIGINS",
                (
                    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
                    if _get_app_env() == "development"
                    else ""
                ),
            )
        )
    )
    cors_origin_regex: str = Field(default_factory=lambda: _get_env_str("CORS_ORIGIN_REGEX"))
    cors_max_age_seconds: int = Field(
        default_factory=lambda: _get_env_int("CORS_MAX_AGE_SECONDS", 600)
    )

    def model_post_init(self, __context) -> None:
        self.database_url = self.database_url.strip()
        if not self.database_url and self.app_env == "development":
            self.database_url = _default_sqlite_database_url()
        self.trusted_user_email = self.trusted_user_email.lower()
        self.dspy_temperature = min(max(self.dspy_temperature, 0.2), 0.4)
        self.sqlite_timeout_seconds = max(1, self.sqlite_timeout_seconds)
        self.auth_window_seconds = max(60, self.auth_window_seconds)
        self.auth_register_limit = max(1, self.auth_register_limit)
        self.auth_login_limit = max(1, self.auth_login_limit)
        self.job_analyze_window_seconds = max(60, self.job_analyze_window_seconds)
        self.job_analyze_limit = max(1, self.job_analyze_limit)
        self.match_cvs_window_seconds = max(60, self.match_cvs_window_seconds)
        self.match_cvs_limit = max(1, self.match_cvs_limit)
        self.cover_letter_window_seconds = max(60, self.cover_letter_window_seconds)
        self.cover_letter_limit = max(1, self.cover_letter_limit)
        self.cv_upload_window_seconds = max(60, self.cv_upload_window_seconds)
        self.cv_upload_limit = max(1, self.cv_upload_limit)
        self.max_pdf_size_mb = max(1, self.max_pdf_size_mb)
        self.max_cvs_per_upload = max(1, self.max_cvs_per_upload)
        self.max_job_description_chars = max(50, self.max_job_description_chars)
        self.max_cv_text_chars = max(500, self.max_cv_text_chars)
        self.max_output_tokens = min(1400, max(50, self.max_output_tokens))
        self.job_analysis_max_tokens = min(1400, max(100, self.job_analysis_max_tokens))
        self.job_analysis_retry_max_tokens = min(
            self.job_analysis_max_tokens,
            max(100, self.job_analysis_retry_max_tokens),
        )
        self.job_preprocess_target_chars = min(
            self.max_job_description_chars,
            max(500, self.job_preprocess_target_chars),
        )
        self.ai_timeout_seconds = max(5, self.ai_timeout_seconds)
        self.frontend_url = self.frontend_url.rstrip("/")
        self.cors_origins = _dedupe_preserve_order(
            self.cors_origins + ([self.frontend_url] if self.frontend_url else [])
        )
        self.cors_max_age_seconds = max(0, self.cors_max_age_seconds)

        if self.app_env == "production" and self.secret_key == "dev-only-secret-key-change-me":
            raise ValueError("SECRET_KEY must be set in production")
        if not self.database_url:
            raise ValueError("DATABASE_URL must be set")
        if self.app_env == "production" and self.database_url.startswith("sqlite"):
            raise ValueError("DATABASE_URL must point to PostgreSQL in production")
        if self.app_env == "production" and not self.is_postgres:
            raise ValueError("DATABASE_URL must use a PostgreSQL driver in production")
        if "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS cannot contain '*' when credentials are enabled")

    @property
    def max_pdf_size_bytes(self) -> int:
        return self.max_pdf_size_mb * 1024 * 1024

    @property
    def dspy_max_tokens(self) -> int:
        return self.max_output_tokens

    @property
    def dspy_timeout_seconds(self) -> int:
        return self.ai_timeout_seconds

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith(("postgresql://", "postgresql+"))

    def is_trusted_user(self, email: str | None) -> bool:
        if not self.trusted_user_email or not email:
            return False
        return email.strip().lower() == self.trusted_user_email

    def should_bypass_user_limits(self, email: str | None) -> bool:
        return self.is_trusted_user(email)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def configure_dspy() -> dspy.LM:
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY is not set")
    lm = dspy.LM(
        model=settings.dspy_model,
        api_key=settings.openrouter_api_key,
        api_base=settings.openrouter_base_url,
        temperature=min(max(settings.dspy_temperature, 0.2), 0.4),
        max_tokens=max(50, min(settings.max_output_tokens, 1400)),
        extra_body={"reasoning": {"enabled": False}},
    )
    dspy.settings.configure(lm=lm)
    return lm
