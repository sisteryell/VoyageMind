import logging
import time
import uuid

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from exceptions import VoyageMindError

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start = time.perf_counter()
        method = request.method
        path = request.url.path

        logger.info("REQ  %s %s [%s]", method, path, request_id)

        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled error  %s %s [%s]", method, path, request_id)
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": request_id},
            )

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "RES  %s %s -> %s (%.1fms) [%s]",
            method, path, response.status_code, elapsed_ms, request_id,
        )

        response.headers["X-Request-ID"] = request_id
        return response


async def voyagemind_exception_handler(_request: Request, exc: VoyageMindError):
    logger.error("Application error: %s", exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
