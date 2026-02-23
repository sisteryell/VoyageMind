import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import get_settings, setup_logging
from exceptions import VoyageMindError
from middleware import RequestLoggingMiddleware, limiter, voyagemind_exception_handler
from routes import router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("%s v%s starting (model=%s)", settings.app_name, settings.app_version, settings.openai_model)
    yield
    logger.info("VoyageMind shutting down")


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="AI-powered multi-agent travel planner",
    version=settings.app_version,
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.allowed_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)
app.add_exception_handler(VoyageMindError, voyagemind_exception_handler)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.app_version}
