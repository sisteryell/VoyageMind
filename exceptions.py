"""
exceptions.py — Custom error types

Instead of using generic Python exceptions everywhere, we define our
own so that:
  1. Every error carries an HTTP status code.
  2. The middleware can catch them all in one place and return a
     clean JSON error response to the client.

Inheritance tree:
    Exception
    └── VoyageMindError          (base, status 500)
        ├── AgentError           (an AI agent failed, status 502)
        └── OpenAIClientError    (OpenAI API unreachable, status 502)
"""


class VoyageMindError(Exception):
    """Base class for all VoyageMind errors."""

    def __init__(self, message: str = "An unexpected error occurred", status_code: int = 500):
        self.message = message        # human-readable description sent to the client
        self.status_code = status_code  # HTTP status code for the response
        super().__init__(self.message)


class AgentError(VoyageMindError):
    """Raised when an AI agent fails to produce a valid result."""

    def __init__(self, agent_name: str, detail: str):
        super().__init__(
            message=f"Agent '{agent_name}' failed: {detail}",
            status_code=502,  # 502 Bad Gateway — upstream service (OpenAI) had an issue
        )
        self.agent_name = agent_name


class OpenAIClientError(VoyageMindError):
    """Raised when all retry attempts to call the OpenAI API have failed."""

    def __init__(self, detail: str):
        super().__init__(message=f"OpenAI API error: {detail}", status_code=502)
