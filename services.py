"""OpenAI client singleton with exponential-backoff retries.

A single AsyncOpenAI instance is shared across all agents to avoid
creating redundant HTTP connections.  The double-checked locking in
``__new__`` guarantees thread-safe lazy initialization.
"""

import asyncio
import logging
from threading import Lock
from typing import Any

from openai import AsyncOpenAI

from config import get_settings
from exceptions import OpenAIClientError

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Singleton wrapper around ``AsyncOpenAI`` with automatic retries."""

    _instance: "OpenAIClient | None" = None
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
        """One-time initialization called from ``__new__`` (not ``__init__``
        to prevent re-running on subsequent ``cls()`` calls)."""
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout,
        )
        self.model = settings.openai_model
        self._max_retries = settings.openai_max_retries

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """Send a chat completion request with exponential-backoff retries.

        Returns the assistant message content as a string.  Raises
        ``OpenAIClientError`` if all retries are exhausted or if the
        model returns empty/missing content (e.g. tool-call responses).
        """
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            kwargs["response_format"] = response_format

        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content
                if not content:
                    raise OpenAIClientError(
                        "Model returned empty content — possibly a tool-call or refusal response"
                    )
                return content
            except OpenAIClientError:
                raise
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
        """Return the singleton instance, creating it on first call."""
        return cls()
