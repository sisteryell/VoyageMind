"""
routes.py — HTTP endpoints

Endpoints:
  GET  /            → serve the HTML page
  GET  /favicon.ico → return nothing (no icon file)
  POST /plan        → run AI agents and return recommendations + itineraries
  POST /chat        → answer follow-up questions about a previous plan
  POST /compare     → plan two countries side-by-side for comparison

Flow for POST /plan:
  1. Receive country, budget, duration, travel_styles from the client.
  2. Select specialist agents dynamically based on the chosen travel styles
     (e.g. ["honeymoon"] → only HoneymoonAgent runs).
     Falls back to all agents if no styles are provided.
  3. Run selected specialist agents IN PARALLEL.
  4. Feed all results into the aggregator agent → top 2 cities.
  5. Run 2 itinerary agents IN PARALLEL (one per top city).
  6. Return everything to the client.

POST /compare runs the same pipeline for two countries at once.
POST /chat sends the user's question + trip context to a chat agent.
"""
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

# APIRouter groups related routes — registered in main.py
router = APIRouter()

# Jinja2Templates renders HTML files from the /templates folder
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# Core planning logic — shared by /plan and /compare
# ---------------------------------------------------------------------------

async def _run_plan(
    country: str,
    budget: str,
    duration: int,
    travel_styles: list[str],
    session_id: str,
) -> dict:
    """
    Full planning pipeline for one country:
      1. Select specialist agents dynamically from TRAVEL_STYLE_AGENT_MAP
         based on the user's chosen travel styles.
         Falls back to all agents if no styles were selected.
      2. Selected agents run IN PARALLEL
      3. Aggregator picks top 2 cities from the combined results
      4. Itinerary agents generate day-by-day plans for each top city

    This is a helper function — not an endpoint itself.
    Both /plan and /compare call it.
    """
    # Shared kwargs passed to every agent prompt template
    agent_kwargs = dict(
        country=country,
        budget=budget,
        duration=duration,
        travel_styles=travel_styles,
        session_id=session_id,
    )

    # Step 1: select agents based on the user's chosen travel styles.
    # If no styles were provided, fall back to running all agents.
    if travel_styles:
        selected = {style: TRAVEL_STYLE_AGENT_MAP[style]
                    for style in travel_styles
                    if style in TRAVEL_STYLE_AGENT_MAP}
    else:
        selected = TRAVEL_STYLE_AGENT_MAP

    styles      = list(selected.keys())
    agent_classes = list(selected.values())

    # Step 2: run only the selected specialist agents IN PARALLEL
    results = await asyncio.gather(
        *(cls().run(**agent_kwargs) for cls in agent_classes)
    )

    # Build labeled results list for the aggregator
    # Each entry tells the aggregator which perspective the recommendations came from
    agent_results = [
        {"agent_name": style, "recommendations": result["recommendations"]}
        for style, result in zip(styles, results)
    ]

    # Step 3: aggregator picks the best overall top-2 cities from all agent results
    final_result = await AggregatorAgent().run(
        **agent_kwargs,
        agent_results=agent_results,
    )

    # Step 4: generate a day-by-day itinerary for each top city (in parallel)
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

    # Combine each city's itinerary with its name
    itineraries = [
        {"city": rec["city"], "days": itin["days"]}
        for rec, itin in zip(final_result["recommendations"], itinerary_results)
    ]

    # agent_details is dynamic — reflects exactly which agents ran this request
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
        "agent_details": agent_details,
    }


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/favicon.ico", status_code=204)
async def favicon():
    """Return 204 No Content — browsers ask for this automatically."""
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@router.post("/plan", response_model=PlanResponse)
@limiter.limit("10/minute")
async def plan_travel(request: Request, plan_request: PlanRequest):
    """
    Main endpoint — called when the user clicks "Explore".
    FastAPI automatically validates plan_request against the PlanRequest schema.
    The `request: Request` parameter is required by the rate limiter.
    """
    country = plan_request.country

    # Generate a unique session ID if the client didn't supply one.
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
    """
    Follow-up chat — the user asks a question about their trip.
    The previous plan context (recommendations, budget, etc.) is sent
    along so the AI can give relevant, personalized answers.
    """
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
    """
    Compare two countries side-by-side.
    Runs the full planning pipeline for both countries in parallel,
    then returns both results together.
    """
    session_id = f"compare-{uuid.uuid4().hex[:12]}"

    logger.info(
        "Comparing '%s' vs '%s'",
        compare_request.country_a,
        compare_request.country_b,
    )

    # Run both plans at the same time — takes the time of one, not two!
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
