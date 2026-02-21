"""
services.py — External API clients (OpenAI and Langfuse)

Both classes use the Singleton pattern, which means only ONE instance
is ever created. Every part of the app shares the same connection,
which is more efficient than creating a new connection on every request.

How the Singleton pattern works here:
  - `_instance` stores the single shared object (None at first).
  - `__new__` is called before `__init__` whenever you do `MyClass()`.
  - We check if `_instance` is already set; if so we return it immediately.
  - A Lock ensures this is safe even if two threads call it at the same time.
"""
import asyncio
import logging
from threading import Lock
from typing import Any, Dict, Optional

from langfuse import Langfuse
from openai import AsyncOpenAI

from config import get_settings
from exceptions import OpenAIClientError

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    A single shared OpenAI client for the whole application.
    Includes automatic retry logic — if a request fails, it tries again
    with increasing wait times (2s, 4s, 8s) before giving up.
    """

    _instance: Optional["OpenAIClient"] = None
    _lock = Lock()  # prevents two threads from creating two instances at once

    def __new__(cls) -> "OpenAIClient":
        # Only create the instance the first time; return the existing one after that
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # double-check inside the lock
                    inst = super().__new__(cls)
                    inst._init()
                    cls._instance = inst
        return cls._instance

    def _init(self) -> None:
        """Called once to set up the OpenAI connection."""
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
        """
        Send a chat message to OpenAI and return the reply as a string.
        Retries automatically on failure using exponential back-off.
        """
        # Build the request parameters
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,  # higher = more creative, lower = more focused
        }
        if response_format:
            kwargs["response_format"] = response_format  # force JSON output from the LLM

        last_error: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self.client.chat.completions.create(**kwargs)
                return response.choices[0].message.content  # the LLM's reply text
            except Exception as exc:
                last_error = exc
                wait = 2 ** attempt  # wait 2s, then 4s, then 8s between retries
                logger.warning(
                    "OpenAI call failed (attempt %d/%d): %s — retrying in %ds",
                    attempt,
                    self._max_retries,
                    exc,
                    wait,
                )
                await asyncio.sleep(wait)

        # All retries exhausted — raise our custom error
        raise OpenAIClientError(str(last_error))

    @classmethod
    def get_instance(cls) -> "OpenAIClient":
        """Convenience method — same as calling OpenAIClient()."""
        return cls()


class LangfuseClient:
    """
    A single shared Langfuse client for tracing and observability.
    Langfuse records what each agent did so you can review it in the dashboard.
    """

    _instance: Optional["LangfuseClient"] = None
    _lock = Lock()

    def __new__(cls) -> "LangfuseClient":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._init()
                    cls._instance = inst
        return cls._instance

    def _init(self) -> None:
        """Called once to connect to Langfuse."""
        settings = get_settings()
        self.client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )

    def flush(self) -> None:
        """Send any unsent traces to Langfuse — called on shutdown."""
        self.client.flush()

    @classmethod
    def get_instance(cls) -> "LangfuseClient":
        """Convenience method — same as calling LangfuseClient()."""
        return cls()
