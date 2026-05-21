import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from app.db import postgres
from app.models import ApiKey, User
from app.services.api_key_service import generate_api_key


async def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/create_api_key.py user@example.com [key-name]")

    email = sys.argv[1].strip().lower()
    key_name = sys.argv[2].strip() if len(sys.argv) > 2 else "Default API key"

    await postgres.init_db()
    if postgres.SessionLocal is None:
        raise SystemExit("DATABASE_URL is not configured")

    raw_key, key_prefix, key_hash = generate_api_key()

    async with postgres.SessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(email=email)
            db.add(user)
            await db.flush()

        db.add(ApiKey(user_id=user.id, name=key_name, key_prefix=key_prefix, key_hash=key_hash))
        await db.commit()

    await postgres.close_db()
    print(raw_key)


if __name__ == "__main__":
    asyncio.run(main())
