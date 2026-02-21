"""
agents.py — AI agent definitions

How it works:
  1. Each agent has a system prompt (sets the AI's role/persona) and
     a user prompt template (filled in with variables at runtime).
  2. The base `Agent` class handles all the common work:
       - Loading prompt files from disk
       - Filling in the template variables (e.g. {{ country }}, {{ budget }})
       - Calling the OpenAI API
       - Parsing and validating the JSON response
  3. Specialist agents only need to declare WHAT files and schema they use.
  4. ItineraryAgent generates day-by-day plans for recommended cities.
  5. ChatAgent answers free-form follow-up questions (returns plain text,
     not JSON — so it overrides run() to skip JSON parsing).

Prompt files live in the /prompts folder:
  - *_system.txt  — tells the AI what role it is playing
  - *_user.txt    — the actual question sent to the AI (uses Jinja2 templating)
"""
import json
import logging
from pathlib import Path
from typing import Type

from jinja2 import Environment, FileSystemLoader
from langfuse.decorators import langfuse_context, observe
from pydantic import BaseModel

from exceptions import AgentError
from schemas import CityRecommendationList, FinalRecommendationList, Itinerary
from services import OpenAIClient

logger = logging.getLogger(__name__)

# Resolve the prompts directory once at import time (not on every request)
_PROMPTS_DIR = Path(__file__).parent / "prompts"

# Jinja2 environment — handles {{ variable }} substitution in .txt templates
_JINJA_ENV = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)))


class Agent:
    """
    Base class shared by all specialist agents.
    Subclasses only need to set four class-level attributes:
        name              — used in log messages and error reports
        system_prompt_file — filename of the system prompt in /prompts
        prompt_template   — filename of the user prompt template in /prompts
        schema            — Pydantic model used to validate the LLM response
    """

    name: str = "BaseAgent"
    prompt_template: str = ""
    system_prompt_file: str = ""
    schema: Type[BaseModel] = CityRecommendationList

    def __init__(self) -> None:
        # Get the shared OpenAI client (created once, reused everywhere)
        self.openai = OpenAIClient.get_instance()

    # --- Prompt loading helpers ---

    def _load_system_prompt(self) -> str:
        """Read the system prompt text file and return its contents."""
        return (_PROMPTS_DIR / self.system_prompt_file).read_text(encoding="utf-8").strip()

    def _render_user_prompt(self, **kwargs: object) -> str:
        """Fill in the Jinja2 template variables (e.g. replace {{ country }} with 'Japan')."""
        return _JINJA_ENV.get_template(self.prompt_template).render(**kwargs)

    # --- Response validation ---

    def _validate(self, raw: dict) -> dict:
        """
        The LLM doesn't always return JSON in the same shape.
        This method tries several common structures before giving up.
        """
        try:
            if isinstance(raw, list):
                # Response is already a list: [{city:...}, ...]
                validated = self.schema.from_list(raw)
            elif "recommendations" in raw:
                # Response is: {"recommendations": [{city:...}, ...]}
                validated = self.schema(**raw)
            elif "cities" in raw:
                validated = self.schema.from_list(raw["cities"])
            elif "result" in raw:
                validated = self.schema.from_list(raw["result"])
            elif "response" in raw:
                validated = self.schema.from_list(raw["response"])
            else:
                # Last resort: find any list value in the response dict
                list_values = [v for v in raw.values() if isinstance(v, list)]
                if list_values:
                    validated = self.schema.from_list(list_values[0])
                else:
                    raise ValueError(f"Unexpected response shape: {list(raw.keys())}")
            return validated.model_dump()  # convert Pydantic model to a plain dict
        except Exception as exc:
            raise AgentError(self.name, f"Validation failed — {exc}") from exc

    # --- Main run method ---

    @observe()  # @observe() records this call in Langfuse for tracing
    async def run(self, **kwargs: object) -> dict:
        """
        Run the agent end-to-end:
          1. Build the system + user messages
          2. Send them to OpenAI
          3. Parse and validate the JSON response
          4. Return a clean Python dict
        """
        # session_id is used for Langfuse grouping — remove it from kwargs
        # before passing the rest to the prompt template
        session_id = kwargs.pop("session_id", None)
        if session_id:
            langfuse_context.update_current_observation(session_id=session_id)

        # OpenAI chat format: a list of messages with roles
        messages = [
            {"role": "system", "content": self._load_system_prompt()},
            {"role": "user",   "content": self._render_user_prompt(**kwargs)},
        ]

        logger.info("Agent '%s' starting", self.name)

        try:
            # Send to OpenAI and get back the raw text reply
            content = await self.openai.chat_completion(
                messages=messages,
                temperature=0.7,
                response_format={"type": "json_object"},  # force JSON output
            )
            # Parse the text into a Python dict
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AgentError(self.name, f"LLM returned invalid JSON: {exc}") from exc

        validated = self._validate(result)
        logger.info("Agent '%s' finished successfully", self.name)
        return validated


# ---------------------------------------------------------------------------
# Specialist agents — each is just 4 lines, everything else is in Agent above
# ---------------------------------------------------------------------------

class HistoryCultureAgent(Agent):
    """Recommends cities based on historical and cultural significance."""
    name = "HistoryCulture"
    prompt_template = "history_culture_user.txt"
    system_prompt_file = "history_culture_system.txt"
    schema = CityRecommendationList


class FoodCuisineAgent(Agent):
    """Recommends cities based on food culture and culinary experiences."""
    name = "FoodCuisine"
    prompt_template = "food_cuisine_user.txt"
    system_prompt_file = "food_cuisine_system.txt"
    schema = CityRecommendationList


class TransportationAgent(Agent):
    """Recommends cities based on transport links and ease of access."""
    name = "Transportation"
    prompt_template = "transportation_user.txt"
    system_prompt_file = "transportation_system.txt"
    schema = CityRecommendationList


class AggregatorAgent(Agent):
    """Picks the top 2 cities from all specialist agents' combined output."""
    name = "Aggregator"
    prompt_template = "aggregator_user.txt"
    system_prompt_file = "aggregator_system.txt"
    schema = FinalRecommendationList


# ---------------------------------------------------------------------------
# New feature agents
# ---------------------------------------------------------------------------

class ItineraryAgent(Agent):
    """
    Generates a day-by-day itinerary for a specific city.
    Called once for each of the aggregator's top-2 cities.
    Uses the Itinerary schema (list of DayPlan objects).
    """
    name = "Itinerary"
    prompt_template = "itinerary_user.txt"
    system_prompt_file = "itinerary_system.txt"
    schema = Itinerary


class ChatAgent(Agent):
    """
    Answers free-form follow-up questions about a trip.
    Unlike other agents, this one returns natural language — NOT JSON —
    so we override run() to skip JSON parsing and validation.
    """
    name = "Chat"
    prompt_template = "chat_user.txt"
    system_prompt_file = "chat_system.txt"

    @observe()
    async def run(self, **kwargs: object) -> dict:
        """
        Chat-specific run:
          1. Build messages from the chat prompt template.
          2. Call OpenAI WITHOUT json_object mode (we want natural text).
          3. Return {"answer": "..."} directly — no JSON parsing needed.
        """
        session_id = kwargs.pop("session_id", None)
        if session_id:
            langfuse_context.update_current_observation(session_id=session_id)

        messages = [
            {"role": "system", "content": self._load_system_prompt()},
            {"role": "user",   "content": self._render_user_prompt(**kwargs)},
        ]

        logger.info("Agent '%s' starting", self.name)

        # No response_format here — we want free-form text, not JSON
        content = await self.openai.chat_completion(
            messages=messages,
            temperature=0.7,
        )

        logger.info("Agent '%s' finished successfully", self.name)
        return {"answer": content}
