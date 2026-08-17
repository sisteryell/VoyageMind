from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from controllers.travel_controller import chat, compare_countries, favicon, health, home, plan_travel
from schemas import ChatRequest, ChatResponse, CompareRequest, PlanRequest, PlanResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def home_controller(request: Request):
    return await home(request)

@router.api_route("/health", methods=["GET", "HEAD"])
async def health_controller():
    return await health()

@router.get("/favicon.ico", status_code=204)
async def favicon_controller():
    return await favicon()

@router.post("/plan", response_model=PlanResponse)
async def plan_travel_controller(request: Request, plan_request: PlanRequest):
    return await plan_travel(request, plan_request)

@router.post("/chat", response_model=ChatResponse)
async def chat_controller(request: Request, chat_request: ChatRequest):
    return await chat(request, chat_request)

@router.post("/compare")
async def compare_countries_controller(request: Request, compare_request: CompareRequest):
    return await compare_countries(request, compare_request)
