from fastapi import APIRouter, Depends

from app.schemas.openrouter import ChatCompletionRequest
from app.services.openrouter import OpenRouterService, get_openrouter_service

router = APIRouter()


@router.post("/chat/completions")
async def create_chat_completion(
    payload: ChatCompletionRequest,
    service: OpenRouterService = Depends(get_openrouter_service),
):
    return await service.create_chat_completion(payload)
