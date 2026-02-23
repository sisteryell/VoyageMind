import asyncio
import logging
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from agents import (
    AggregatorAgent,
    ChatAgent,
    ItineraryAgent,
    TRAVEL_STYLE_AGENT_MAP,
)
from middleware import limiter
from schemas import (
    ChatRequest,
    ChatResponse,
    CompareRequest,
    PlanRequest,
    PlanResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


async def _run_plan(
    country: str,
    budget: str,
    duration: int,
    travel_styles: list[str],
    session_id: str,
) -> dict:
    agent_kwargs = dict(
        country=country,
        budget=budget,
        duration=duration,
        travel_styles=travel_styles,
        session_id=session_id,
    )

    if travel_styles:
        selected = {style: TRAVEL_STYLE_AGENT_MAP[style]
                    for style in travel_styles
                    if style in TRAVEL_STYLE_AGENT_MAP}
    else:
        selected = TRAVEL_STYLE_AGENT_MAP

    styles = list(selected.keys())
    agent_classes = list(selected.values())

    results = await asyncio.gather(
        *(cls().run(**agent_kwargs) for cls in agent_classes)
    )

    agent_results = [
        {"agent_name": style, "recommendations": result["recommendations"]}
        for style, result in zip(styles, results)
    ]

    final_result = await AggregatorAgent().run(
        **agent_kwargs,
        agent_results=agent_results,
    )

    itinerary_results = await asyncio.gather(
        *(
            ItineraryAgent().run(
                city=rec["city"],
                country=country,
                budget=budget,
                duration=duration,
                travel_styles=travel_styles,
                reason=rec["reason"],
                session_id=session_id,
            )
            for rec in final_result["recommendations"]
        )
    )

    itineraries = [
        {"city": rec["city"], "days": itin["days"]}
        for rec, itin in zip(final_result["recommendations"], itinerary_results)
    ]

    agent_details = {
        style: result["recommendations"]
        for style, result in zip(styles, results)
    }

    return {
        "country": country,
        "budget": budget,
        "duration": duration,
        "travel_styles": travel_styles,
        "recommendations": final_result["recommendations"],
        "itineraries": itineraries,
        "agent_details": agent_details,
    }


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/favicon.ico", status_code=204)
async def favicon():
    return Response(status_code=204)


@router.post("/plan", response_model=PlanResponse)
@limiter.limit("10/minute")
async def plan_travel(request: Request, plan_request: PlanRequest):
    country = plan_request.country
    session_id = plan_request.session_id or f"voyage-{uuid.uuid4().hex[:12]}"
    logger.info("Planning travel for '%s' [session=%s]", country, session_id)

    result = await _run_plan(
        country=country,
        budget=plan_request.budget,
        duration=plan_request.duration,
        travel_styles=plan_request.travel_styles,
        session_id=session_id,
    )

    logger.info("Travel plan complete for '%s'", country)
    return PlanResponse(**result, session_id=session_id)


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(request: Request, chat_request: ChatRequest):
    session_id = f"chat-{uuid.uuid4().hex[:12]}"
    logger.info("Chat question for '%s': %s", chat_request.country, chat_request.question[:80])

    result = await ChatAgent().run(
        country=chat_request.country,
        budget=chat_request.budget,
        duration=chat_request.duration,
        travel_styles=chat_request.travel_styles,
        recommendations=chat_request.recommendations,
        question=chat_request.question,
        session_id=session_id,
    )

    return ChatResponse(answer=result["answer"])


@router.post("/compare")
@limiter.limit("5/minute")
async def compare_countries(request: Request, compare_request: CompareRequest):
    session_id = f"compare-{uuid.uuid4().hex[:12]}"
    logger.info("Comparing '%s' vs '%s'", compare_request.country_a, compare_request.country_b)

    result_a, result_b = await asyncio.gather(
        _run_plan(
            country=compare_request.country_a,
            budget=compare_request.budget,
            duration=compare_request.duration,
            travel_styles=compare_request.travel_styles,
            session_id=session_id,
        ),
        _run_plan(
            country=compare_request.country_b,
            budget=compare_request.budget,
            duration=compare_request.duration,
            travel_styles=compare_request.travel_styles,
            session_id=session_id,
        ),
    )

    return {"country_a": result_a, "country_b": result_b}
