import logging
import uuid

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        except HTTPException as exc:
            if isinstance(exc.detail, dict) and "message" in exc.detail and "code" in exc.detail:
                error = exc.detail
            else:
                error = {"message": str(exc.detail), "code": "HTTP_ERROR"}

            return JSONResponse(
                status_code=exc.status_code,
                content={"success": False, "error": error, "request_id": request_id},
                headers={"X-Request-ID": request_id},
            )
        except Exception:
            logger.exception("Unhandled request error", extra={"request_id": request_id})
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": {"message": "Internal server error", "code": "INTERNAL_SERVER_ERROR"},
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )
