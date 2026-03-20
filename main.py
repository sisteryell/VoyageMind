import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import get_settings, setup_logging
from exceptions import VoyageMindError
from middleware import RequestLoggingMiddleware, limiter, voyagemind_exception_handler
from routes import router

logger = logging.getLogger(__name__)


def _format_validation_error(exc: RequestValidationError) -> str:
    messages = []
    for error in exc.errors():
        loc = " → ".join(str(p) for p in error.get("loc", []) if p != "body")
        msg = error.get("msg", "Invalid value")
        # Strip the "Value error, " prefix Pydantic v2 prepends to @field_validator messages
        msg = msg.removeprefix("Value error, ")
        messages.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(messages)


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


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": _format_validation_error(exc)},
    )
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.app_version}
