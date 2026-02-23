import asyncio
import logging
from threading import Lock
from typing import Any, Dict, Optional

from openai import AsyncOpenAI

from config import get_settings
from exceptions import OpenAIClientError

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Singleton wrapper around AsyncOpenAI with exponential-backoff retries."""

    _instance: Optional["OpenAIClient"] = None
    _lock = Lock()

    def __new__(cls) -> "OpenAIClient":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._init()
                    cls._instance = inst
        return cls._instance

    def _init(self) -> None:
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout,
        )
        self.model = settings.openai_model
        self._max_retries = settings.openai_max_retries

    async def chat_completion(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            kwargs["response_format"] = response_format

        last_error: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self.client.chat.completions.create(**kwargs)
                return response.choices[0].message.content
            except Exception as exc:
                last_error = exc
                wait = 2 ** attempt
                logger.warning(
                    "OpenAI attempt %d/%d failed: %s — retrying in %ds",
                    attempt, self._max_retries, exc, wait,
                )
                await asyncio.sleep(wait)

        raise OpenAIClientError(str(last_error))

    @classmethod
    def get_instance(cls) -> "OpenAIClient":
        return cls()
