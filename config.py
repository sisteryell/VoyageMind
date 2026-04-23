import logging
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    openai_api_key: str = Field(...)
    openai_model: str = Field("gpt-4o-mini")
    openai_timeout: int = Field(60)
    openai_max_retries: int = Field(3)

    openai_embedding_model: str = Field("text-embedding-3-small")
    rag_similarity_threshold: float = Field(0.35)
    rag_persist_directory: str = Field("data/chroma_db")
    admin_api_key: str = Field(...)

    app_name: str = Field("VoyageMind")
    app_version: str = Field("2.0.0")
    debug: bool = Field(False)
    log_level: str = Field("INFO")
    allowed_origins: str = Field("*")
    rate_limit: str = Field("10/minute")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def setup_logging(level: str = "INFO") -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
