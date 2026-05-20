import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.db import postgres
from app.services.api_key_service import get_api_key_record, mark_api_key_used

logger = logging.getLogger(__name__)

PROTECTED_PATHS = ("/api/v1/youtube-summarizer",)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.api_key_auth_enabled or not request.url.path.startswith(PROTECTED_PATHS):
            return await call_next(request)

        if postgres.SessionLocal is None:
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": {"message": "API key authentication is unavailable", "code": "AUTH_UNAVAILABLE"},
                },
            )

        raw_token = self._extract_bearer_token(request)
        if not raw_token:
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": {"message": "Missing Bearer API key", "code": "MISSING_API_KEY"},
                },
            )

        async with postgres.SessionLocal() as db:
            api_key = await get_api_key_record(db, raw_token)
            if api_key is None:
                logger.info("Invalid API key rejected", extra={"path": request.url.path})
                return JSONResponse(
                    status_code=401,
                    content={
                        "success": False,
                        "error": {"message": "Invalid API key", "code": "INVALID_API_KEY"},
                    },
                )

            request.state.api_key_id = api_key.id
            request.state.user_id = api_key.user_id
            await mark_api_key_used(db, api_key)

        return await call_next(request)

    def _extract_bearer_token(self, request: Request) -> str:
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return ""
        return token.strip()
