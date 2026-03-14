from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from controllers.travel_controller import (
    chat as chat_controller,
    compare_countries as compare_countries_controller,
    favicon as favicon_controller,
    home as home_controller,
    plan_travel as plan_travel_controller,
)
from middleware import limiter
from schemas import ChatRequest, ChatResponse, CompareRequest, PlanRequest, PlanResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return await home_controller(request)

@router.get("/favicon.ico", status_code=204)
async def favicon():
    return await favicon_controller()

@router.post("/plan", response_model=PlanResponse)
@limiter.limit("3/minute")
async def plan_travel(request: Request, plan_request: PlanRequest):
    return await plan_travel_controller(request, plan_request)

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat(request: Request, chat_request: ChatRequest):
    return await chat_controller(request, chat_request)

@router.post("/compare")
@limiter.limit("5/minute")
async def compare_countries(request: Request, compare_request: CompareRequest):
    return await compare_countries_controller(request, compare_request)
