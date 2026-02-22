"""
config.py — Application settings

pydantic-settings reads values from your .env file automatically.
If a required value is missing, the app will refuse to start with
a clear error message instead of crashing later at runtime.
"""
import logging
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All configuration lives here.
    Values are loaded from the .env file (or real environment variables).
    Fields marked with `...` are REQUIRED — the app won't start without them.
    Fields with a default value are optional.
    """

    # Tell pydantic-settings to read from a .env file in the project root.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- OpenAI settings ---
    openai_api_key: str = Field(..., description="Your OpenAI API key (required)")
    openai_model: str = Field("gpt-4o-mini", description="Which OpenAI model to use")
    openai_timeout: int = Field(60, description="Seconds to wait before giving up on a request")
    openai_max_retries: int = Field(3, description="How many times to retry a failed request")

    # --- General app settings ---
    app_name: str = Field("VoyageMind", description="Application name shown in the API docs")
    app_version: str = Field("2.0.0", description="Current version")
    debug: bool = Field(False, description="Set to true during local development")
    log_level: str = Field("INFO", description="Log verbosity: DEBUG, INFO, WARNING, ERROR")
    allowed_origins: str = Field("*", description="Comma-separated list of allowed CORS origins")
    rate_limit: str = Field("10/minute", description="Max requests per user per time window")


# @lru_cache means this function is only called ONCE — the same Settings
# object is reused on every subsequent call, which is more efficient.
@lru_cache
def get_settings() -> Settings:
    """Return the application settings (cached after the first call)."""
    return Settings()


def setup_logging(level: str = "INFO") -> None:
    """Set up a clean, readable log format for the whole application."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Reduce noise from third-party libraries — we only want our own logs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
