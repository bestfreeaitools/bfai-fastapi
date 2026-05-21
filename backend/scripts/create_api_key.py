import asyncio
import hashlib
import secrets
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DB_OPERATION_TIMEOUT_SECONDS = 20


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def generate_api_key() -> tuple[str, str, str]:
    raw_key = f"bfai_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return raw_key, raw_key[:16], key_hash


async def main() -> None:
    sql_only = "--sql-only" in sys.argv
    args = [arg for arg in sys.argv[1:] if arg != "--sql-only"]

    if len(args) < 1:
        raise SystemExit("Usage: python scripts/create_api_key.py [--sql-only] user@example.com [key-name]")

    email = args[0].strip().lower()
    key_name = args[1].strip() if len(args) > 1 else "Default API key"
    raw_key, key_prefix, key_hash = generate_api_key()

    if sql_only:
        print_sql_only(email=email, key_name=key_name, raw_key=raw_key, key_prefix=key_prefix, key_hash=key_hash)
        return

    from app.core.config import settings

    if not settings.database_url.startswith(("postgresql://", "postgresql+asyncpg://")):
        raise SystemExit(
            "DATABASE_URL is not configured or is invalid. "
            "Use a PostgreSQL URL, not SUPABASE_URL. Example: postgresql://postgres:password@host:5432/postgres"
        )

    try:
        await asyncio.wait_for(
            create_key(
                database_url=settings.database_url,
                connect_timeout=settings.database_connect_timeout_seconds,
                email=email,
                key_name=key_name,
                key_prefix=key_prefix,
                key_hash=key_hash,
            ),
            timeout=DB_OPERATION_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise SystemExit(
            "Timed out connecting to the database. Check Coolify DATABASE_URL, Supabase pooler host, password, and SSL settings. "
            "You can also run: python scripts/create_api_key.py --sql-only user@example.com \"Production key\""
        ) from exc

    log("API key created successfully. Store this value now; it will not be shown again.")
    print(raw_key, flush=True)


async def create_key(
    database_url: str,
    connect_timeout: int,
    email: str,
    key_name: str,
    key_prefix: str,
    key_hash: str,
) -> None:
    import asyncpg

    log("Connecting to database...")
    dsn, ssl = normalize_asyncpg_dsn(database_url)
    connection = await asyncpg.connect(
        dsn=dsn,
        ssl=ssl,
        timeout=connect_timeout,
        command_timeout=connect_timeout,
    )

    try:
        log(f"Creating API key for {email}...")
        async with connection.transaction():
            user_id = await connection.fetchval(
                """
                insert into users (email)
                values ($1)
                on conflict (email) do update set updated_at = now()
                returning id
                """,
                email,
            )
            await connection.execute(
                """
                insert into api_keys (user_id, name, key_prefix, key_hash)
                values ($1, $2, $3, $4)
                """,
                user_id,
                key_name,
                key_prefix,
                key_hash,
            )
    finally:
        await connection.close()


def normalize_asyncpg_dsn(database_url: str) -> tuple[str, str | None]:
    dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlsplit(dsn)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    sslmode = query.pop("sslmode", None)
    normalized_dsn = urlunsplit(parsed._replace(query=urlencode(query)))

    if sslmode in {"require", "verify-ca", "verify-full"}:
        return normalized_dsn, "require"
    return normalized_dsn, None


def print_sql_only(email: str, key_name: str, raw_key: str, key_prefix: str, key_hash: str) -> None:
    escaped_email = sql_quote(email)
    escaped_key_name = sql_quote(key_name)
    escaped_key_prefix = sql_quote(key_prefix)
    escaped_key_hash = sql_quote(key_hash)

    log("No database connection will be opened. Run this SQL in Supabase SQL Editor.")
    print(f"API_KEY={raw_key}")
    print(
        f"""
with created_user as (
    insert into users (email)
    values ({escaped_email})
    on conflict (email) do update set updated_at = now()
    returning id
)
insert into api_keys (user_id, name, key_prefix, key_hash)
select id, {escaped_key_name}, {escaped_key_prefix}, {escaped_key_hash}
from created_user;
""".strip()
    )


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        raise SystemExit("Cancelled")
