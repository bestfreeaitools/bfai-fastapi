import asyncio
import logging
import re
from urllib.parse import parse_qs, urlparse

from fastapi import HTTPException, status
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled, YouTubeTranscriptApi

from app.core.config import settings

logger = logging.getLogger(__name__)

VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(url: str) -> str:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().removeprefix("www.")

    if host in {"youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith(("/shorts/", "/embed/")):
            video_id = parsed.path.rstrip("/").split("/")[-1]
        else:
            video_id = ""
    elif host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    else:
        video_id = ""

    if not VIDEO_ID_PATTERN.fullmatch(video_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Invalid YouTube URL", "code": "INVALID_YOUTUBE_URL"},
        )

    return video_id


async def fetch_transcript(video_id: str) -> str:
    try:
        transcript = await asyncio.wait_for(
            asyncio.to_thread(YouTubeTranscriptApi.get_transcript, video_id),
            timeout=settings.youtube_transcript_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"message": "Timed out while fetching transcript", "code": "TRANSCRIPT_TIMEOUT"},
        ) from exc
    except (NoTranscriptFound, TranscriptsDisabled) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Transcript is not available for this video", "code": "TRANSCRIPT_NOT_FOUND"},
        ) from exc
    except Exception as exc:
        logger.exception("YouTube transcript fetch failed", extra={"video_id": video_id})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"message": "Unable to fetch YouTube transcript", "code": "TRANSCRIPT_FETCH_FAILED"},
        ) from exc

    text = " ".join(item.get("text", "").replace("\n", " ") for item in transcript)
    return re.sub(r"\s+", " ", text).strip()
