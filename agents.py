"""
Simplified agents module - all agents in one file.
"""
from pathlib import Path
import json
from jinja2 import Environment, FileSystemLoader
from langfuse.decorators import observe, langfuse_context
from services import OpenAIClient
from schemas import CityRecommendationList, FinalRecommendationList

class Agent:
    """Base agent class with simplified logic."""
    
    def __init__(self, name: str, prompt_template: str, system_prompt_file: str):
        self.name = name
        self.prompt_template = prompt_template
        self.system_prompt_file = system_prompt_file
        
        # Singleton
        self.openai = OpenAIClient.get_instance()
        
        # Setup templates
        prompts_dir = Path(__file__).parent / "prompts"
        self.prompts_dir = prompts_dir
        self.jinja_env = Environment(loader=FileSystemLoader(str(prompts_dir)))
    
    def load_system_prompt(self) -> str:
        """Load system prompt from file."""
        path = self.prompts_dir / self.system_prompt_file
        return path.read_text(encoding='utf-8').strip()
    
    def render_user_prompt(self, **kwargs) -> str:
        """Render Jinja2 user prompt template."""
        template = self.jinja_env.get_template(self.prompt_template)
        return template.render(**kwargs)
    
    @observe()
    async def run(self, **kwargs) -> dict:
        """Execute agent with Langfuse tracing."""
        # Extract session_id if provided
        session_id = kwargs.pop('session_id', None)
        if session_id:
            langfuse_context.update_current_observation(session_id=session_id)
        
        # Build messages
        messages = [
            {"role": "system", "content": self.load_system_prompt()},
            {"role": "user", "content": self.render_user_prompt(**kwargs)}
        ]
        
        # Call OpenAI
        response = await self.openai.chat_completion(
            messages=messages,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        # Parse and validate
        result = json.loads(response)
        validated = self.validate(result)
        
        return validated
    
    def validate(self, response: dict) -> dict:
        """Override in subclass."""
        return response


class HistoryCultureAgent(Agent):
    """History & culture specialist."""
    
    def __init__(self):
        super().__init__(
            name="HistoryCulture",
            prompt_template="history_culture.jinja",
            system_prompt_file="history_culture_system.txt"
        )
    
    def validate(self, response: dict) -> dict:
        if isinstance(response, list):
            validated = CityRecommendationList.from_list(response)
        elif "recommendations" in response:
            validated = CityRecommendationList(**response)
        elif "cities" in response:
            validated = CityRecommendationList.from_list(response["cities"])
        else:
            raise ValueError(f"Unexpected response: {response}")
        return validated.model_dump()


class FoodCuisineAgent(Agent):
    """Food & cuisine specialist."""
    
    def __init__(self):
        super().__init__(
            name="FoodCuisine",
            prompt_template="food_cuisine.jinja",
            system_prompt_file="food_cuisine_system.txt"
        )
    
    def validate(self, response: dict) -> dict:
        if isinstance(response, list):
            validated = CityRecommendationList.from_list(response)
        elif "recommendations" in response:
            validated = CityRecommendationList(**response)
        elif "cities" in response:
            validated = CityRecommendationList.from_list(response["cities"])
        else:
            raise ValueError(f"Unexpected response: {response}")
        return validated.model_dump()


class TransportationAgent(Agent):
    """Transportation & connectivity specialist."""
    
    def __init__(self):
        super().__init__(
            name="Transportation",
            prompt_template="transportation.jinja",
            system_prompt_file="transportation_system.txt"
        )
    
    def validate(self, response: dict) -> dict:
        if isinstance(response, list):
            validated = CityRecommendationList.from_list(response)
        elif "recommendations" in response:
            validated = CityRecommendationList(**response)
        elif "cities" in response:
            validated = CityRecommendationList.from_list(response["cities"])
        else:
            raise ValueError(f"Unexpected response: {response}")
        return validated.model_dump()


class AggregatorAgent(Agent):
    """Aggregates all agent recommendations."""
    
    def __init__(self):
        super().__init__(
            name="Aggregator",
            prompt_template="aggregator.jinja",
            system_prompt_file="aggregator_system.txt"
        )
    
    def validate(self, response: dict) -> dict:
        if isinstance(response, list):
            validated = FinalRecommendationList.from_list(response)
        elif "recommendations" in response:
            validated = FinalRecommendationList(**response)
        elif "cities" in response:
            validated = FinalRecommendationList.from_list(response["cities"])
        elif "result" in response:
            validated = FinalRecommendationList.from_list(response["result"])
        else:
            raise ValueError(f"Unexpected response: {response}")
        return validated.model_dump()
