import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings, setup_logging
from exceptions import VoyageMindError
from routes import router

logger = logging.getLogger(__name__)


def _format_validation_error(exc: RequestValidationError) -> str:
    messages = []
    for error in exc.errors():
        loc = " → ".join(str(p) for p in error.get("loc", []) if p != "body")
        msg = error.get("msg", "Invalid value")
        msg = msg.removeprefix("Value error, ")
        messages.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(messages)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info(f"{settings.app_name} v{settings.app_version} starting (model={settings.openai_model})")
    yield
    logger.info("VoyageMind shutting down")


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="AI-powered multi-agent travel planner",
    version=settings.app_version,
    lifespan=lifespan,
)

async def voyagemind_exception_handler(_request: Request, exc: VoyageMindError):
    logger.error(f"Application error: {exc.message}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

app.add_exception_handler(VoyageMindError, voyagemind_exception_handler)

@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    request_id = str(uuid.uuid4())[:8]
    logger.exception(f"Unhandled error [{request_id}]")
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )
    response.headers["X-Request-ID"] = request_id
    return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": _format_validation_error(exc)},
    )

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": settings.app_version}
