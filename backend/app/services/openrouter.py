import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.openrouter import ChatCompletionRequest


class OpenRouterService:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def create_chat_completion(self, payload: ChatCompletionRequest) -> dict:
        if not self.api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OpenRouter API key is not configured",
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": str(settings.site_url or "https://bestfreeaitools.io"),
            "X-Title": settings.openrouter_app_title,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload.model_dump(exclude_none=True),
                )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OpenRouter request failed",
            ) from exc

        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text

            raise HTTPException(
                status_code=response.status_code,
                detail=detail,
            )

        return response.json()


def get_openrouter_service() -> OpenRouterService:
    return OpenRouterService(
        api_key=settings.openrouter_api_key,
        base_url=str(settings.openrouter_base_url),
    )
