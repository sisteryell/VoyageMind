"""
API routes for VoyageMind.
"""
import asyncio
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from pathlib import Path
from langfuse.decorators import observe, langfuse_context
from agents import HistoryCultureAgent, FoodCuisineAgent, TransportationAgent, AggregatorAgent


router = APIRouter()
templates = Jinja2Templates(directory="templates")


class PlanRequest(BaseModel):
    """Request schema."""
    country: str = Field(..., min_length=1)
    session_id: str = Field(default=None, description="Optional session ID for tracking")


class PlanResponse(BaseModel):
    """Response schema."""
    country: str
    recommendations: list[dict]
    agent_details: dict
    session_id: str


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page."""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/favicon.ico")
async def favicon():
    """Return a simple response for favicon."""
    return {"status": "no favicon"}


@router.post("/plan", response_model=PlanResponse)
@observe()
async def plan_travel(plan_request: PlanRequest):
    """Plan travel for a country with session tracking."""
    try:
        country = plan_request.country.strip()
        
        # Generate or use provided session ID
        session_id = plan_request.session_id or f"voyage-{uuid.uuid4().hex[:12]}"
        
        # Update current observation with session_id
        langfuse_context.update_current_observation(session_id=session_id)
        
        # Initialize agents
        history = HistoryCultureAgent()
        food = FoodCuisineAgent()
        transport = TransportationAgent()
        aggregator = AggregatorAgent()
        
        # Run agents in parallel (each will have session_id in trace)
        history_result, food_result, transport_result = await asyncio.gather(
            history.run(country=country, session_id=session_id),
            food.run(country=country, session_id=session_id),
            transport.run(country=country, session_id=session_id)
        )
        
        # Get final recommendations
        final_result = await aggregator.run(
            country=country,
            session_id=session_id,
            history_recommendations=history_result["recommendations"],
            food_recommendations=food_result["recommendations"],
            transportation_recommendations=transport_result["recommendations"]
        )
        
        return PlanResponse(
            country=country,
            recommendations=final_result["recommendations"],
            agent_details={
                "history_culture": history_result["recommendations"],
                "food_cuisine": food_result["recommendations"],
                "transportation": transport_result["recommendations"]
            },
            session_id=session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error planning travel: {str(e)}")
