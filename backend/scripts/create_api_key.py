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

DB_OPERATION_TIMEOUT_SECONDS = 20


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


async def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/create_api_key.py user@example.com [key-name]")

    email = sys.argv[1].strip().lower()
    key_name = sys.argv[2].strip() if len(sys.argv) > 2 else "Default API key"

    log("Initializing database connection...")
    await postgres.init_db()
    if postgres.SessionLocal is None:
        raise SystemExit(
            "DATABASE_URL is not configured or is invalid. "
            "Use a PostgreSQL URL, not SUPABASE_URL. Example: postgresql://postgres:password@host:5432/postgres"
        )

    try:
        raw_key = await asyncio.wait_for(
            create_key(email=email, key_name=key_name),
            timeout=DB_OPERATION_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise SystemExit(
            "Timed out connecting to the database. Check Coolify DATABASE_URL, Supabase pooler host, password, and SSL settings."
        ) from exc
    finally:
        await postgres.close_db()

    log("API key created successfully. Store this value now; it will not be shown again.")
    print(raw_key, flush=True)


async def create_key(email: str, key_name: str) -> str:
    raw_key, key_prefix, key_hash = generate_api_key()

    log(f"Creating API key for {email}...")
    async with postgres.SessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            log("User does not exist yet; creating user row...")
            user = User(email=email)
            db.add(user)
            await db.flush()

        db.add(ApiKey(user_id=user.id, name=key_name, key_prefix=key_prefix, key_hash=key_hash))
        await db.commit()

    return raw_key


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        raise SystemExit("Cancelled")
