from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field


class YouTubeSummarizerRequest(BaseModel):
    youtube_url: AnyHttpUrl = Field(..., description="Full YouTube video URL")
    model_route: Literal["fast", "smart"] = Field(default="fast", description="Model route for summarization")
    max_tokens: int | None = Field(default=None, ge=100, le=2000)
    temperature: float | None = Field(default=None, ge=0, le=1)


class YouTubeSummaryData(BaseModel):
    video_id: str
    summary: str
    key_points: list[str]


class UsageData(BaseModel):
    model: str
    tokens: int


class YouTubeSummarizerResponse(BaseModel):
    success: bool = True
    cached: bool = False
    data: YouTubeSummaryData
    usage: UsageData


class ErrorDetail(BaseModel):
    message: str
    code: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
