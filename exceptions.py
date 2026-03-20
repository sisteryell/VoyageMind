"""Application-specific exception hierarchy.

All custom exceptions inherit from VoyageMindError so that a single
exception handler in middleware can catch them and return a safe JSON
response without leaking internal details.
"""


class VoyageMindError(Exception):
    """Base exception for all VoyageMind application errors."""

    def __init__(self, message: str = "An unexpected error occurred", status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AgentError(VoyageMindError):
    """Raised when an AI agent fails during prompt rendering, LLM call, or validation."""

    def __init__(self, agent_name: str, detail: str):
        super().__init__(message=f"Agent '{agent_name}' failed: {detail}", status_code=502)
        self.agent_name = agent_name


class OpenAIClientError(VoyageMindError):
    """Raised when the OpenAI API returns an error after all retries are exhausted."""

    def __init__(self, detail: str):
        super().__init__(message=f"OpenAI API error: {detail}", status_code=502)
