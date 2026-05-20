# BFAI FastAPI Backend

Production-lean FastAPI starter optimized for async AI API workloads.

## Architecture

```text
backend/
  app/
    api/
      routes/          # HTTP endpoints
      router.py        # API router composition
    core/              # config and logging
    db/                # PostgreSQL and Redis clients
    middleware/        # request/error middleware
    models/            # SQLAlchemy models
    schemas/           # Pydantic request/response models
    services/          # reusable integrations such as OpenRouter
    main.py            # application factory and lifespan wiring
  Dockerfile
  requirements.txt
  .env.example
```

## Local Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Health Checks

- `GET /health` for simple platform health checks.
- `GET /api/v1/health/ready` for dependency readiness checks.

## Deployment Notes

- Set secrets in Coolify environment variables, not in Git.
- Keep `DOCS_ENABLED=false` in production unless docs are protected.
- Use Supabase's pooler connection string for serverless or container platforms with many replicas.
- Keep `CORS_ORIGINS` restricted to your frontend domains. Use comma-separated values, for example `https://bestfreeaitools.io,https://www.bestfreeaitools.io`.
- Coolify should use `/health` as the health check path and expose port `8000`.
- The container binds to `0.0.0.0` and respects Coolify's `PORT` environment variable.
- `localhost`, `127.0.0.1`, and `::1` are allowed internally so Docker/Coolify health checks can pass with `TrustedHostMiddleware` enabled.

## API Keys

Apply `db/schema.sql` in Supabase, then create a key:

```bash
python scripts/create_api_key.py user@example.com "Production key"
```

Use the printed value as `Authorization: Bearer YOUR_API_KEY`.
