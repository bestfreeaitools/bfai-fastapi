import json
import logging
import re
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import settings
from app.db import postgres
from app.schemas.youtube_summarizer import (
    ErrorResponse,
    UsageData,
    YouTubeSummarizerRequest,
    YouTubeSummarizerResponse,
    YouTubeSummaryData,
)
from app.services.api_key_service import log_api_usage_by_ids
from app.services.cache_service import CacheService, get_cache_service
from app.services.openrouter_service import OpenRouterClient, get_openrouter_client
from app.services.youtube_service import extract_video_id, fetch_transcript

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/youtube-summarizer",
    response_model=YouTubeSummarizerResponse,
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
    summary="Summarize a YouTube video",
)
async def summarize_youtube_video(
    payload: YouTubeSummarizerRequest,
    request: Request,
    cache: CacheService = Depends(get_cache_service),
    ai: OpenRouterClient = Depends(get_openrouter_client),
) -> YouTubeSummarizerResponse:
    video_id = extract_video_id(str(payload.youtube_url))
    cache_key = f"youtube_summary:{video_id}"

    cached = await cache.get_json(cache_key)
    if cached:
        return YouTubeSummarizerResponse(
            success=True,
            cached=True,
            data=YouTubeSummaryData(**cached["data"]),
            usage=UsageData(model=cached.get("model", "cache"), tokens=0),
        )

    transcript = await fetch_transcript(video_id)
    if not transcript:
        raise HTTPException(
            status_code=422,
            detail={"message": "Transcript is empty", "code": "EMPTY_TRANSCRIPT"},
        )

    transcript = transcript[: settings.youtube_summary_max_transcript_chars]
    ai_result = await ai.generate_completion(
        messages=_build_summary_messages(transcript),
        model_route=payload.model_route,
        max_tokens=payload.max_tokens,
        temperature=payload.temperature,
    )
    summary_data = _parse_summary_response(video_id, ai_result.content)

    await cache.set_json(
        cache_key,
        {"data": summary_data.model_dump(), "model": ai_result.model},
        ttl_seconds=settings.youtube_summary_cache_ttl_seconds,
    )

    await _log_usage(
        request=request,
        model=ai_result.model,
        prompt_tokens=ai_result.prompt_tokens,
        completion_tokens=ai_result.completion_tokens,
        total_tokens=ai_result.total_tokens,
    )

    logger.info(
        "YouTube summary generated",
        extra={"video_id": video_id, "model": ai_result.model, "tokens": ai_result.total_tokens},
    )

    return YouTubeSummarizerResponse(
        success=True,
        cached=False,
        data=summary_data,
        usage=UsageData(model=ai_result.model, tokens=ai_result.total_tokens),
    )


def _build_summary_messages(transcript: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You summarize YouTube transcripts for an AI tools platform. "
                "Return only valid JSON with keys: summary and key_points. "
                "summary must be concise and useful. key_points must be an array of 4 to 8 strings."
            ),
        },
        {
            "role": "user",
            "content": f"Summarize this transcript:\n\n{transcript}",
        },
    ]


def _parse_summary_response(video_id: str, content: str) -> YouTubeSummaryData:
    cleaned = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.IGNORECASE | re.MULTILINE).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        parsed = {"summary": content.strip(), "key_points": []}

    return YouTubeSummaryData(
        video_id=video_id,
        summary=str(parsed.get("summary", "")).strip() or content.strip(),
        key_points=[str(item).strip() for item in parsed.get("key_points", []) if str(item).strip()],
    )


async def _log_usage(
    request: Request,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
) -> None:
    user_id = getattr(request.state, "user_id", None)
    api_key_id = getattr(request.state, "api_key_id", None)
    if user_id is None or api_key_id is None or postgres.SessionLocal is None:
        return

    try:
        async with postgres.SessionLocal() as db:
            await log_api_usage_by_ids(
                db=db,
                user_id=user_id,
                api_key_id=api_key_id,
                endpoint=str(request.url.path),
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost=_estimate_cost(prompt_tokens, completion_tokens),
            )
    except Exception:
        logger.exception("Usage logging failed", extra={"endpoint": str(request.url.path)})


def _estimate_cost(prompt_tokens: int, completion_tokens: int) -> Decimal:
    prompt_cost = Decimal(str(settings.ai_prompt_cost_per_million_tokens))
    completion_cost = Decimal(str(settings.ai_completion_cost_per_million_tokens))
    return ((Decimal(prompt_tokens) * prompt_cost) + (Decimal(completion_tokens) * completion_cost)) / Decimal(1000000)
