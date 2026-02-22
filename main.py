"""
main.py — VoyageMind application entry point

This is where FastAPI is created and everything is wired together.

To start the server, run:
    uvicorn main:app --reload
"""
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


# ---------------------------------------------------------------------------
# Lifespan — code here runs ONCE on startup, and once again on shutdown.
# FastAPI calls the part before `yield` when the server starts,
# and the part after `yield` when the server stops.
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    settings = get_settings()
    setup_logging(settings.log_level)          # configure log format/level
    logger.info(
        "%s v%s starting (model=%s)",
        settings.app_name,
        settings.app_version,
        settings.openai_model,
    )

    yield  # <-- server is running while we wait here

    # --- Shutdown ---
    logger.info("VoyageMind shutting down")


# ---------------------------------------------------------------------------
# Create the FastAPI app
# ---------------------------------------------------------------------------
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="AI-powered multi-agent travel planner",
    version=settings.app_version,
    lifespan=lifespan,
)

# Allow the browser to call our API from any origin.
# In production you should restrict this to your frontend's domain.
origins = [o.strip() for o in settings.allowed_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Log every request/response and handle our custom errors nicely.
app.add_middleware(RequestLoggingMiddleware)
app.add_exception_handler(VoyageMindError, voyagemind_exception_handler)

# Rate limiting — attach the limiter to the app and register its error handler.
# When a client exceeds the limit (e.g. 10/minute), they get a 429 Too Many Requests.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Serve static files (CSS, JS) from the /static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register all routes defined in routes.py
app.include_router(router)


# ---------------------------------------------------------------------------
# Health-check endpoint — useful for monitoring tools to verify the app is up
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.app_version}
