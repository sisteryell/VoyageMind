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
    name: str = "BaseAgent"
    prompt_template: str = ""
    system_prompt_file: str = ""
    schema: Type[BaseModel] = CityRecommendationList

    def __init__(self) -> None:
        self.openai = OpenAIClient.get_instance()

    def _load_system_prompt(self, **kwargs: object) -> str:
        return _JINJA_ENV.get_template(self.system_prompt_file).render(**kwargs).strip()

    def _render_user_prompt(self, **kwargs: object) -> str:
        return _JINJA_ENV.get_template(self.prompt_template).render(**kwargs)

    def _validate(self, raw: dict) -> dict:
        try:
            if isinstance(raw, dict) and "error" in raw:
                raise ValueError(str(raw.get("error") or "Model reported an error"))

            if isinstance(raw, list):
                validated = _from_list(raw)
            elif "days" in raw:
                validated = self.schema(**raw)
            elif "recommendations" in raw:
                if isinstance(raw["recommendations"], list):
                    validated = self.schema.from_list(raw["recommendations"])
                else:
                    validated = self.schema(**raw)
            elif "cities" in raw:
                validated = _from_list(raw["cities"])
            elif "result" in raw:
                validated = _from_list(raw["result"])
            elif "response" in raw:
                validated = _from_list(raw["response"])
            else:
                list_values = [v for v in raw.values() if isinstance(v, list)]
                if list_values:
                    validated = _from_list(list_values[0])
                else:
                    raise ValueError(f"Unexpected response shape: {list(raw.keys())}")
            return validated.model_dump()
        except Exception as exc:
            raise AgentError(self.name, f"Validation failed — {exc}") from exc

    async def run(self, **kwargs: object) -> dict:
        kwargs.pop("session_id", None)

        messages = [
            {"role": "system", "content": self._load_system_prompt(**kwargs)},
            {"role": "user", "content": self._render_user_prompt(**kwargs)},
        ]

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

        validated = self._validate(result, **kwargs)
        logger.info(f"Agent '{self.name}' finished")
        return validated


class HistoryCultureAgent(Agent):
    name = "HistoryCulture"
    prompt_template = "history_culture/user.txt"
    system_prompt_file = "history_culture/system.txt"
    schema = CityRecommendationList

class FoodCuisineAgent(Agent):
    name = "FoodCuisine"
    prompt_template = "food_cuisine/user.txt"
    system_prompt_file = "food_cuisine/system.txt"
    schema = CityRecommendationList

class TransportationAgent(Agent):
    name = "Transportation"
    prompt_template = "transportation/user.txt"
    system_prompt_file = "transportation/system.txt"
    schema = CityRecommendationList

class AggregatorAgent(Agent):
    name = "Aggregator"
    prompt_template = "aggregator/user.txt"
    system_prompt_file = "aggregator/system.txt"
    schema = FinalRecommendationList

class AdventureAgent(Agent):
    name = "Adventure"
    prompt_template = "adventure/user.txt"
    system_prompt_file = "adventure/system.txt"
    schema = CityRecommendationList

class RelaxationAgent(Agent):
    name = "Relaxation"
    prompt_template = "relaxation/user.txt"
    system_prompt_file = "relaxation/system.txt"
    schema = CityRecommendationList

class FamilyAgent(Agent):
    name = "Family"
    prompt_template = "family/user.txt"
    system_prompt_file = "family/system.txt"
    schema = CityRecommendationList

class HoneymoonAgent(Agent):
    name = "Honeymoon"
    prompt_template = "honeymoon/user.txt"
    system_prompt_file = "honeymoon/system.txt"
    schema = CityRecommendationList

class SoloAgent(Agent):
    name = "Solo"
    prompt_template = "solo/user.txt"
    system_prompt_file = "solo/system.txt"
    schema = CityRecommendationList

class NatureAgent(Agent):
    name = "Nature"
    prompt_template = "nature/user.txt"
    system_prompt_file = "nature/system.txt"
    schema = CityRecommendationList

TRAVEL_STYLE_AGENT_MAP: dict[str, type[Agent]] = {
    "adventure":  AdventureAgent,
    "relaxation": RelaxationAgent,
    "family":     FamilyAgent,
    "honeymoon":  HoneymoonAgent,
    "solo":       SoloAgent,
    "culture":    HistoryCultureAgent,
    "food":       FoodCuisineAgent,
    "nature":     NatureAgent,
}

class ItineraryAgent(Agent):
    name = "Itinerary"
    prompt_template = "itinerary/user.txt"
    system_prompt_file = "itinerary/system.txt"
    schema = Itinerary

class ChatAgent(Agent):
    name = "Chat"
    prompt_template = "chat/user.txt"
    system_prompt_file = "chat/system.txt"

    async def run(self, **kwargs: object) -> dict:
        kwargs.pop("session_id", None)

        messages = [
            {"role": "system", "content": self._load_system_prompt(**kwargs)},
            {"role": "user",   "content": self._render_user_prompt(**kwargs)},
        ]

        logger.info(f"Agent '{self.name}' starting")

        content = await self.openai.chat_completion(
            messages=messages,
            temperature=0.7,
        )

        logger.info(f"Agent '{self.name}' finished")
        return {"answer": content}
