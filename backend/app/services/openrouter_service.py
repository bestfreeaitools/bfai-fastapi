import asyncio
import logging
from dataclasses import dataclass
from typing import Literal

import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

ModelRoute = Literal["fast", "smart", "fallback"]


@dataclass(slots=True)
class AICompletionResult:
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class OpenRouterClient:
    def __init__(self) -> None:
        self.api_key = settings.openrouter_api_key
        self.base_url = str(settings.openrouter_base_url).rstrip("/")
        self.timeout = settings.openrouter_timeout_seconds
        self.max_retries = settings.openrouter_max_retries

    def resolve_model(self, route: ModelRoute = "fast") -> str:
        models = {
            "fast": settings.openrouter_fast_model,
            "smart": settings.openrouter_smart_model,
            "fallback": settings.openrouter_fallback_model,
        }
        return models[route]

    async def generate_completion(
        self,
        messages: list[dict[str, str]],
        model_route: ModelRoute = "fast",
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AICompletionResult:
        if not self.api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"message": "OpenRouter API key is not configured", "code": "OPENROUTER_NOT_CONFIGURED"},
            )

        model = self.resolve_model(model_route)
        payload = {
            "model": model,
            "messages": messages,
            "temperature": settings.youtube_summary_temperature if temperature is None else temperature,
            "max_tokens": settings.youtube_summary_max_tokens if max_tokens is None else max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": str(settings.site_url or "https://bestfreeaitools.io"),
            "X-Title": settings.openrouter_app_title,
        }

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                if response.status_code < 500:
                    return self._parse_response(response, model)

                logger.warning(
                    "OpenRouter server error",
                    extra={"status_code": response.status_code, "attempt": attempt + 1, "model": model},
                )
                last_error = HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"message": "OpenRouter server error", "code": "OPENROUTER_SERVER_ERROR"},
                )
            except httpx.TimeoutException as exc:
                logger.warning("OpenRouter timeout", extra={"attempt": attempt + 1, "model": model})
                last_error = exc
            except httpx.RequestError as exc:
                logger.warning("OpenRouter request failed", extra={"attempt": attempt + 1, "model": model})
                last_error = exc

            if attempt < self.max_retries:
                await asyncio.sleep(0.5 * (attempt + 1))

        if isinstance(last_error, HTTPException):
            raise last_error

        fallback_model = self.resolve_model("fallback")
        if model != fallback_model:
            logger.info("Retrying OpenRouter with fallback model", extra={"fallback_model": fallback_model})
            return await self.generate_completion(
                messages=messages,
                model_route="fallback",
                max_tokens=max_tokens,
                temperature=temperature,
            )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": "OpenRouter request failed", "code": "OPENROUTER_REQUEST_FAILED"},
        )

    def _parse_response(self, response: httpx.Response, requested_model: str) -> AICompletionResult:
        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = {"message": response.text, "code": "OPENROUTER_ERROR"}
            raise HTTPException(status_code=response.status_code, detail=detail)

        data = response.json()
        choices = data.get("choices") or []
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        usage = data.get("usage") or {}

        if not content:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={"message": "OpenRouter returned an empty response", "code": "OPENROUTER_EMPTY_RESPONSE"},
            )

        return AICompletionResult(
            content=content,
            model=data.get("model") or requested_model,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            total_tokens=int(usage.get("total_tokens") or 0),
        )


def get_openrouter_client() -> OpenRouterClient:
    return OpenRouterClient()
