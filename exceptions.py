class VoyageMindError(Exception):
    def __init__(self, message: str = "An unexpected error occurred", status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AgentError(VoyageMindError):
    def __init__(self, agent_name: str, detail: str):
        super().__init__(message=f"Agent '{agent_name}' failed: {detail}", status_code=502)
        self.agent_name = agent_name


class OpenAIClientError(VoyageMindError):
    def __init__(self, detail: str):
        super().__init__(message=f"OpenAI API error: {detail}", status_code=502)
