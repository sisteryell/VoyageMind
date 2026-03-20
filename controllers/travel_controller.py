"""Controller layer — request orchestration and response shaping.

Each public function corresponds to an API endpoint.  Controllers
receive validated request models, delegate to the TravelModel, and
return structured response models.
"""

import asyncio
import logging
import uuid

from fastapi import Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from models.travel_model import TravelModel
from schemas import (
    ChatRequest,
    ChatResponse,
    CompareRequest,
    PlanRequest,
    PlanResponse,
)

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="templates")
travel_model = TravelModel()


async def home(request: Request) -> HTMLResponse:
    """Serve the single-page application."""
    return templates.TemplateResponse("index.html", {"request": request})


async def favicon() -> Response:
    """Return an empty 204 for browsers requesting /favicon.ico."""
    return Response(status_code=204)


async def plan_travel(request: Request, plan_request: PlanRequest) -> PlanResponse:
    """Generate city recommendations and day-by-day itineraries."""
    country = plan_request.country
    session_id = plan_request.session_id or f"voyage-{uuid.uuid4().hex[:12]}"
    logger.info("Planning travel for %s [session=%s]", country, session_id)

    result = await travel_model.run_plan(
        country=country,
        budget=plan_request.budget,
        duration=plan_request.duration,
        city_count=plan_request.city_count,
        travel_styles=plan_request.travel_styles,
        session_id=session_id
    )

    logger.info("Travel plan complete for %s", country)
    return result


async def chat(request: Request, chat_request: ChatRequest) -> ChatResponse:
    """Answer a follow-up question in the context of a previous plan."""
    session_id = f"chat-{uuid.uuid4().hex[:12]}"
    logger.info("Chat question for %s: %.80s", chat_request.country, chat_request.question)

    result = await travel_model.run_chat(
        country=chat_request.country,
        budget=chat_request.budget,
        duration=chat_request.duration,
        travel_styles=chat_request.travel_styles,
        recommendations=chat_request.recommendations,
        question=chat_request.question,
        session_id=session_id,
    )

    return ChatResponse(answer=result["answer"])


async def compare_countries(request: Request, compare_request: CompareRequest) -> dict:
    """Run two travel plans in parallel and return both for comparison."""
    session_id = f"compare-{uuid.uuid4().hex[:12]}"
    logger.info("Comparing %s vs %s", compare_request.country_a, compare_request.country_b)

    result_a, result_b = await asyncio.gather(
        travel_model.run_plan(
            country=compare_request.country_a,
            budget=compare_request.budget,
            duration=compare_request.duration,
            city_count=2,
            travel_styles=compare_request.travel_styles,
            session_id=session_id,
        ),
        travel_model.run_plan(
            country=compare_request.country_b,
            budget=compare_request.budget,
            duration=compare_request.duration,
            city_count=2,
            travel_styles=compare_request.travel_styles,
            session_id=session_id,
        ),
    )

    return {"country_a": result_a.model_dump(), "country_b": result_b.model_dump()}
