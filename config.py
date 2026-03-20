"""Application configuration loaded from environment variables and ``.env``.

``get_settings()`` is cached so the ``.env`` file is read only once.
``setup_logging()`` configures the root logger and silences noisy
third-party libraries.
"""

import logging
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, validated application settings sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    openai_api_key: str = Field(...)
    openai_model: str = Field("gpt-4o-mini")
    openai_timeout: int = Field(60)
    openai_max_retries: int = Field(3)

    app_name: str = Field("VoyageMind")
    app_version: str = Field("2.0.0")
    debug: bool = Field(False)
    log_level: str = Field("INFO")
    allowed_origins: str = Field("*")
    rate_limit: str = Field("10/minute")


@lru_cache
def get_settings() -> Settings:
    """Return the singleton Settings instance (reads .env on first call)."""
    return Settings()


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger and suppress noisy HTTP-client loggers."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
