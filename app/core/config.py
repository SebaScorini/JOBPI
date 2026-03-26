import os
from pathlib import Path
from secrets import token_urlsafe

import dspy
from dotenv import load_dotenv
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", override=True)


class Settings(BaseModel):
    openrouter_api_key: str = Field(default=os.getenv("OPENROUTER_API_KEY", ""))
    openrouter_base_url: str = Field(
        default=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    )
    database_url: str = Field(default=os.getenv("DATABASE_URL", "sqlite:///./jobpi.db"))
    jwt_secret_key: str = Field(default=os.getenv("JWT_SECRET_KEY", token_urlsafe(32)))
    access_token_expire_minutes: int = Field(default=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")))
    dspy_model: str = Field(default=os.getenv("DSPY_MODEL", "openrouter/minimax/minimax-m2.5:free"))
    dspy_temperature: float = Field(default=float(os.getenv("DSPY_TEMPERATURE", "0")))
    dspy_max_tokens: int = Field(default=int(os.getenv("DSPY_MAX_TOKENS", "1500")))
    dspy_timeout_seconds: int = Field(default=int(os.getenv("DSPY_TIMEOUT_SECONDS", "60")))
    cors_origins: list[str] = Field(default_factory=lambda: _parse_csv_setting(
        os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
        )
    ))


def _parse_csv_setting(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def get_settings() -> Settings:
    settings = Settings()
    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY is not set")
    return settings


def configure_dspy() -> dspy.LM:
    settings = get_settings()
    lm = dspy.LM(
        model=settings.dspy_model,
        api_key=settings.openrouter_api_key,
        api_base=settings.openrouter_base_url,
        temperature=settings.dspy_temperature,
        max_tokens=settings.dspy_max_tokens,
        extra_body={"reasoning": {"enabled": False}},
    )
    dspy.settings.configure(lm=lm)
    return lm
