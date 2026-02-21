"""
middleware.py — Request logging, error handling, and rate limiting

Middleware sits between the web server and your route functions.
Every incoming request passes through here first, and every outgoing
response passes through here last — making it the perfect place to:
  - Assign a unique ID to each request (great for debugging)
  - Log how long each request took
  - Catch unhandled errors and return a tidy JSON response
  - Limit how fast any single client can hit the API (rate limiting)
"""
import logging
import time
import uuid

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from config import get_settings
from exceptions import VoyageMindError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiter — shared by routes.py and main.py
# Uses the client's IP address to track per-user request counts.
# The default limit (e.g. "10/minute") comes from config.py / .env.
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Runs around every HTTP request.
    - Generates a short unique request ID (e.g. "a3f9bc12").
    - Logs the incoming request and the outgoing response with timing.
    - Adds an X-Request-ID header to the response so clients can reference it.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Create a short ID we can use to trace this specific request in logs
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id  # make it available to route functions

        start = time.perf_counter()
        method = request.method   # GET, POST, etc.
        path = request.url.path   # e.g. /plan

        logger.info("REQ  %s %s [%s]", method, path, request_id)

        try:
            response = await call_next(request)  # hand off to the actual route handler
        except Exception:
            # This catches truly unexpected crashes that slipped past everything else
            logger.exception("Unhandled error  %s %s [%s]", method, path, request_id)
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": request_id},
            )

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "RES  %s %s -> %s (%.1fms) [%s]",
            method,
            path,
            response.status_code,
            elapsed_ms,
            request_id,
        )

        # Attach the request ID to the response headers — useful for debugging
        response.headers["X-Request-ID"] = request_id
        return response


async def voyagemind_exception_handler(_request: Request, exc: VoyageMindError):
    """
    Converts any VoyageMindError (and its subclasses) into a JSON response.
    This is registered in main.py so FastAPI calls it automatically.
    """
    logger.error("Application error: %s", exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
