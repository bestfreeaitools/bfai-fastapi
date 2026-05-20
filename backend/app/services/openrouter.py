from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.openrouter import ChatCompletionRequest
from app.services.openrouter_service import get_openrouter_client


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

        client = get_openrouter_client()
        result = await client.generate_completion(
            messages=[message.model_dump() for message in payload.messages],
            max_tokens=payload.max_tokens,
            temperature=payload.temperature,
        )
        return {
            "model": result.model,
            "choices": [{"message": {"role": "assistant", "content": result.content}}],
            "usage": {
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "total_tokens": result.total_tokens,
            },
        }


def get_openrouter_service() -> OpenRouterService:
    return OpenRouterService(
        api_key=settings.openrouter_api_key,
        base_url=str(settings.openrouter_base_url),
    )
