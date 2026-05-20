from fastapi import APIRouter

from app.db.postgres import check_db
from app.db.redis import check_redis

router = APIRouter()


@router.get("/health")
async def health():
    return {"health": "ok"}


@router.get("/health/ready")
async def readiness():
    db_ok = await check_db()
    redis_ok = await check_redis()
    return {
        "status": "ready" if db_ok and redis_ok else "degraded",
        "database": db_ok,
        "redis": redis_ok,
    }
