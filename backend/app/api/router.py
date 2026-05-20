from fastapi import APIRouter

from app.api.routes import health, openrouter

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(openrouter.router, prefix="/openrouter", tags=["openrouter"])
