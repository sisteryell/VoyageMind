"""AI agent classes that interact with OpenAI to produce travel recommendations.

Each travel style has a dedicated Agent subclass whose only difference is the
prompt directory and display name.  The base Agent handles prompt rendering,
LLM communication, and response validation in a single reusable flow.

Agent pipeline:
    StyleAgents (parallel) → AggregatorAgent → ItineraryAgent
    ChatAgent handles free-form follow-up questions (no JSON parsing).
"""

import inspect
import json
import logging
from pathlib import Path
from typing import Type

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

from exceptions import AgentError
from schemas import CityRecommendationList, FinalRecommendationList, Itinerary
from services import OpenAIClient

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_JINJA_ENV = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)))


class Agent:
    """Base agent that sends a system + user prompt pair to the LLM and
    validates the JSON response against a Pydantic schema.

    Subclasses only need to set *name*, *prompt_template*,
    *system_prompt_file*, and optionally *schema*.
    """

    name: str = "BaseAgent"
    prompt_template: str = ""
    system_prompt_file: str = ""
    schema: Type[BaseModel] = CityRecommendationList

    def __init__(self) -> None:
        self.openai = OpenAIClient.get_instance()

    # ------------------------------------------------------------------
    # Prompt helpers
    # ------------------------------------------------------------------

    def _load_system_prompt(self, **kwargs: object) -> str:
        """Render the Jinja2 system prompt template with the given context."""
        return _JINJA_ENV.get_template(self.system_prompt_file).render(**kwargs).strip()

    def _render_user_prompt(self, **kwargs: object) -> str:
        """Render the Jinja2 user prompt template with the given context."""
        return _JINJA_ENV.get_template(self.prompt_template).render(**kwargs)

    def _build_messages(self, **kwargs: object) -> list[dict[str, str]]:
        """Assemble the system + user message list for the LLM call."""
        return [
            {"role": "system", "content": self._load_system_prompt(**kwargs)},
            {"role": "user", "content": self._render_user_prompt(**kwargs)},
        ]

    # ------------------------------------------------------------------
    # Response validation
    # ------------------------------------------------------------------

    def _from_list(self, data: list, city_count: int | None = None) -> BaseModel:
        """Delegate to ``self.schema.from_list``, forwarding *city_count* when the
        schema's factory accepts it."""
        sig = inspect.signature(self.schema.from_list)
        if "city_count" in sig.parameters and city_count is not None:
            return self.schema.from_list(data, city_count=city_count)
        return self.schema.from_list(data)

    def _extract_payload(self, raw: dict | list) -> dict | list:
        """Normalize the LLM response into the shape expected by *self.schema*.

        LLM outputs vary — sometimes a bare list, sometimes wrapped in keys
        like ``recommendations``, ``cities``, ``result``, or ``response``.
        This method peels away the wrapper so ``_validate`` can focus on
        schema construction.
        """
        if isinstance(raw, list):
            return raw

        if "error" in raw:
            raise ValueError(str(raw.get("error") or "Model reported an error"))

        if "days" in raw:
            return raw

        if "recommendations" in raw:
            value = raw["recommendations"]
            return value if isinstance(value, list) else raw

        for key in ("cities", "result", "response"):
            if key in raw and isinstance(raw[key], list):
                return raw[key]

        list_values = [v for v in raw.values() if isinstance(v, list)]
        if list_values:
            return list_values[0]

        raise ValueError(f"Unexpected response shape: {list(raw.keys())}")

    def _validate(self, raw: dict | list, city_count: int | None = None) -> dict:
        """Parse and validate the raw LLM output against *self.schema*."""
        try:
            payload = self._extract_payload(raw)
            if isinstance(payload, list):
                validated = self._from_list(payload, city_count)
            else:
                validated = self.schema(**payload)
            return validated.model_dump()
        except Exception as exc:
            raise AgentError(self.name, f"Validation failed — {exc}") from exc

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def run(
        self,
        country: str,
        budget: str,
        duration: int,
        city_count: int,
        travel_styles: list[str],
        agent_results: list[dict] | None = None,
        city: str | None = None,
        reason: str | None = None
    ) -> dict:
        """Execute the agent: render prompts → call LLM (JSON mode) → validate."""
        context = {
            "country": country,
            "budget": budget,
            "duration": duration,
            "city_count": city_count,
            "travel_styles": travel_styles
        }
        for key, value in {"agent_results": agent_results, "city": city, "reason": reason}.items():
            if value is not None:
                context[key] = value

        messages = self._build_messages(**context)

        logger.info(f"Agent '{self.name}' starting")

        try:
            content = await self.openai.chat_completion(
                messages=messages,
                temperature=0.7,
                response_format={"type": "json_object"},
            )
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AgentError(self.name, f"LLM returned invalid JSON: {exc}") from exc

        validated = self._validate(result, city_count=city_count)
        logger.info(f"Agent '{self.name}' finished")
        return validated


# ---------------------------------------------------------------------------
# Travel-style specialist agents
# ---------------------------------------------------------------------------

class HistoryCultureAgent(Agent):
    """Recommends cities strong in museums, heritage sites, and local history."""
    name = "HistoryCulture"
    prompt_template = "history_culture/user.txt"
    system_prompt_file = "history_culture/system.txt"
    schema = CityRecommendationList


class FoodCuisineAgent(Agent):
    """Recommends cities strong in street food, local restaurants, and food markets."""
    name = "FoodCuisine"
    prompt_template = "food_cuisine/user.txt"
    system_prompt_file = "food_cuisine/system.txt"
    schema = CityRecommendationList


class TransportationAgent(Agent):
    """Recommends cities with good transportation connectivity."""
    name = "Transportation"
    prompt_template = "transportation/user.txt"
    system_prompt_file = "transportation/system.txt"
    schema = CityRecommendationList


class AdventureAgent(Agent):
    """Recommends cities strong in hiking, extreme sports, and outdoor activities."""
    name = "Adventure"
    prompt_template = "adventure/user.txt"
    system_prompt_file = "adventure/system.txt"
    schema = CityRecommendationList


class RelaxationAgent(Agent):
    """Recommends cities strong in spas, beaches, and slow-paced retreats."""
    name = "Relaxation"
    prompt_template = "relaxation/user.txt"
    system_prompt_file = "relaxation/system.txt"
    schema = CityRecommendationList


class FamilyAgent(Agent):
    """Recommends cities strong in kid-friendly activities, safety, and convenience."""
    name = "Family"
    prompt_template = "family/user.txt"
    system_prompt_file = "family/system.txt"
    schema = CityRecommendationList


class HoneymoonAgent(Agent):
    """Recommends cities strong in romantic spots, fine dining, and scenic stays."""
    name = "Honeymoon"
    prompt_template = "honeymoon/user.txt"
    system_prompt_file = "honeymoon/system.txt"
    schema = CityRecommendationList


class SoloAgent(Agent):
    """Recommends cities strong in budget tips, safety, and solo-friendly experiences."""
    name = "Solo"
    prompt_template = "solo/user.txt"
    system_prompt_file = "solo/system.txt"
    schema = CityRecommendationList


class NatureAgent(Agent):
    """Recommends cities near national parks, wildlife, and scenic landscapes."""
    name = "Nature"
    prompt_template = "nature/user.txt"
    system_prompt_file = "nature/system.txt"
    schema = CityRecommendationList


TRAVEL_STYLE_AGENT_MAP: dict[str, type[Agent]] = {
    "adventure": AdventureAgent,
    "relaxation": RelaxationAgent,
    "family": FamilyAgent,
    "honeymoon": HoneymoonAgent,
    "solo": SoloAgent,
    "culture": HistoryCultureAgent,
    "food": FoodCuisineAgent,
    "nature": NatureAgent,
}


# ---------------------------------------------------------------------------
# Aggregation and itinerary agents
# ---------------------------------------------------------------------------

class AggregatorAgent(Agent):
    """Merges specialist-agent results into a ranked list of final city picks."""
    name = "Aggregator"
    prompt_template = "aggregator/user.txt"
    system_prompt_file = "aggregator/system.txt"
    schema = FinalRecommendationList


class ItineraryAgent(Agent):
    """Builds a day-by-day itinerary for a single recommended city."""
    name = "Itinerary"
    prompt_template = "itinerary/user.txt"
    system_prompt_file = "itinerary/system.txt"
    schema = Itinerary


# ---------------------------------------------------------------------------
# Chat agent (free-form text, no JSON parsing)
# ---------------------------------------------------------------------------

class ChatAgent(Agent):
    """Handles follow-up questions — returns plain-text answers (no JSON mode)."""
    name = "Chat"
    prompt_template = "chat/user.txt"
    system_prompt_file = "chat/system.txt"

    async def run(
        self,
        country: str,
        budget: str,
        duration: int,
        travel_styles: list[str],
        recommendations: list[dict],
        question: str
    ) -> dict:
        """Execute the chat agent: render prompts → call LLM (text mode) → return answer."""
        context = {
            "country": country,
            "budget": budget,
            "duration": duration,
            "travel_styles": travel_styles,
            "recommendations": recommendations,
            "question": question
        }
        messages = self._build_messages(**context)

        logger.info(f"Agent '{self.name}' starting")

        content = await self.openai.chat_completion(
            messages=messages,
            temperature=0.7,
        )

        logger.info(f"Agent '{self.name}' finished")
        return {"answer": content}
