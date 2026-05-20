import hashlib
import secrets
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApiKey, ApiUsage


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    raw_key = f"bfai_{secrets.token_urlsafe(32)}"
    return raw_key, raw_key[:16], hash_api_key(raw_key)


async def get_api_key_record(db: AsyncSession, raw_key: str) -> ApiKey | None:
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_hash == hash_api_key(raw_key),
            ApiKey.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def mark_api_key_used(db: AsyncSession, api_key: ApiKey) -> None:
    api_key.last_used_at = datetime.utcnow()
    await db.commit()


async def log_api_usage(
    db: AsyncSession,
    api_key: ApiKey,
    endpoint: str,
    model: str | None,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    estimated_cost: Decimal = Decimal("0"),
) -> None:
    db.add(
        ApiUsage(
            user_id=api_key.user_id,
            api_key_id=api_key.id,
            endpoint=endpoint,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
        )
    )
    await db.commit()


async def log_api_usage_by_ids(
    db: AsyncSession,
    user_id: UUID,
    api_key_id: UUID,
    endpoint: str,
    model: str | None,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    estimated_cost: Decimal = Decimal("0"),
) -> None:
    db.add(
        ApiUsage(
            user_id=user_id,
            api_key_id=api_key_id,
            endpoint=endpoint,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
        )
    )
    await db.commit()
