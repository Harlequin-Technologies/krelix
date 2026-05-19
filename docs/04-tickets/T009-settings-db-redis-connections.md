# T009 — Settings module + DB/Redis connections + /readyz wiring

**Status:** Not started
**Phase:** 2 — Database foundation + auth
**Estimated session length:** 2 hr
**Depends on:** T005
**Blocks:** T010, T011, T012, T014, T015, T016
**Maps to:** `stack.md` (Pydantic Settings, asyncpg, redis-py); `architecture.md` Component 2 (Control Plane); `deployment.md` env var contract; `auth-and-security.md` "Secrets Management" (KRELIX_SECRET_KEY).

---

## Objective

Add a typed config module reading all required environment variables, an async SQLAlchemy engine + session factory for Postgres, a Redis client, and wire both into `/readyz` so the endpoint actually verifies DB and Redis reachability. The app should refuse to start if `KRELIX_SECRET_KEY` is missing or too short.

## Context

Every subsequent backend ticket needs to read config and talk to Postgres or Redis. Centralizing this in one ticket prevents inconsistent per-ticket env-var reading and makes mocking straightforward in tests.

## Read for context

- [`../03-technical/stack.md`](../03-technical/stack.md) — `pydantic-settings`, `asyncpg`, `redis-py`
- [`../03-technical/deployment.md`](../03-technical/deployment.md) — env var contract (DATABASE_URL, REDIS_URL, KRELIX_SECRET_KEY, KRELIX_BIND_HOST/PORT)
- [`../03-technical/auth-and-security.md`](../03-technical/auth-and-security.md) — "Secrets Management" section
- [`T005-control-plane-dockerfile-fastapi-skeleton.md`](T005-control-plane-dockerfile-fastapi-skeleton.md) — the FastAPI app this extends

## Files to create

- `backend/src/krelix/config.py` — `Settings` class (pydantic-settings) with all env vars
- `backend/src/krelix/db.py` — async engine + `AsyncSession` factory + FastAPI dependency `get_db`
- `backend/src/krelix/redis_client.py` — singleton async Redis client + FastAPI dependency `get_redis`
- `backend/tests/test_readyz_real.py` — integration test that hits a real Postgres + Redis (uses Compose dev services)
- `backend/tests/conftest.py` — pytest fixtures: anyio backend, an httpx async client, a clean DB fixture (the table-truncation strategy is fine for now since T011 hasn't landed; this is a placeholder fixture that will get fleshed out in T011)

## Files to modify

- `backend/src/krelix/main.py` — replace the placeholder `/readyz` with one that actually pings DB + Redis using the new clients; add startup/shutdown lifespan hooks to open and close them.
- `backend/pyproject.toml` — no new deps (everything's already in T002), but verify `asyncpg` and `redis` are present.

## Files to NOT touch

- ORM models (T010), migrations (T011), auth (T013–T016), API routes for entities — all later
- `agent/`, `frontend/`

## Steps

1. **Write `backend/src/krelix/config.py`:**
   ```python
   from functools import lru_cache
   from pydantic import Field, SecretStr
   from pydantic_settings import BaseSettings, SettingsConfigDict

   class Settings(BaseSettings):
       model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

       database_url: str = Field(..., alias="DATABASE_URL")
       redis_url: str = Field(..., alias="REDIS_URL")
       secret_key: SecretStr = Field(..., alias="KRELIX_SECRET_KEY", min_length=32)
       bind_host: str = Field("0.0.0.0", alias="KRELIX_BIND_HOST")
       bind_port: int = Field(8000, alias="KRELIX_BIND_PORT")

   @lru_cache
   def get_settings() -> Settings:
       return Settings()  # type: ignore[call-arg]
   ```

   - `min_length=32` ensures a too-short `KRELIX_SECRET_KEY` is rejected at startup with a clean Pydantic validation error.
   - `SecretStr` keeps the key out of repr / logs.

2. **Write `backend/src/krelix/db.py`:**
   ```python
   from collections.abc import AsyncIterator
   from contextlib import asynccontextmanager
   from sqlalchemy.ext.asyncio import (
       AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine,
   )
   from .config import get_settings

   _engine: AsyncEngine | None = None
   _session_factory: async_sessionmaker[AsyncSession] | None = None

   def init_engine() -> None:
       global _engine, _session_factory
       settings = get_settings()
       _engine = create_async_engine(settings.database_url, pool_size=5, max_overflow=10)
       _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

   async def dispose_engine() -> None:
       global _engine, _session_factory
       if _engine is not None:
           await _engine.dispose()
       _engine = None
       _session_factory = None

   async def get_db() -> AsyncIterator[AsyncSession]:
       assert _session_factory is not None, "DB not initialized"
       async with _session_factory() as session:
           yield session

   async def ping_db() -> bool:
       assert _engine is not None
       async with _engine.connect() as conn:
           await conn.execute(text("SELECT 1"))
       return True
   ```

3. **Write `backend/src/krelix/redis_client.py`:**
   ```python
   from redis.asyncio import Redis, from_url
   from .config import get_settings

   _client: Redis | None = None

   def init_redis() -> None:
       global _client
       _client = from_url(get_settings().redis_url, decode_responses=True)

   async def dispose_redis() -> None:
       global _client
       if _client is not None:
           await _client.aclose()
       _client = None

   def get_redis() -> Redis:
       assert _client is not None, "Redis not initialized"
       return _client

   async def ping_redis() -> bool:
       assert _client is not None
       return await _client.ping()
   ```

4. **Update `backend/src/krelix/main.py`** to use FastAPI's lifespan:
   ```python
   from contextlib import asynccontextmanager
   from fastapi import FastAPI
   from .db import init_engine, dispose_engine, ping_db
   from .redis_client import init_redis, dispose_redis, ping_redis
   from .logging import configure_logging

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       configure_logging()
       init_engine()
       init_redis()
       yield
       await dispose_redis()
       await dispose_engine()

   def create_app() -> FastAPI:
       app = FastAPI(title="Krelix Control Plane", version="0.0.1", lifespan=lifespan)

       @app.get("/healthz")
       async def healthz() -> dict[str, str]:
           return {"status": "ok"}

       @app.get("/readyz")
       async def readyz() -> dict[str, str]:
           db_ok = await ping_db()
           redis_ok = await ping_redis()
           if db_ok and redis_ok:
               return {"status": "ready"}
           # FastAPI's HTTPException returns the right status code
           from fastapi import HTTPException
           raise HTTPException(status_code=503, detail={"db": db_ok, "redis": redis_ok})

       return app

   app = create_app()
   ```

5. **Update `backend/tests/conftest.py`** with shared fixtures: pytest-asyncio mode, httpx AsyncClient wired to the ASGI app. Mark tests requiring real DB/Redis with `@pytest.mark.integration` so unit tests don't need them.

6. **Write `backend/tests/test_readyz_real.py`** — marked as integration; verifies `/readyz` returns 200 when DB + Redis are reachable, and 503 when one is down (simulated by tearing down Redis).

7. **Update existing `backend/tests/test_health.py`** to keep working — since `/readyz` now pings DB+Redis, the unit-test version of `/readyz` needs DB+Redis mocked or this test is moved to integration. Move it to integration if it's simpler.

8. **Update `backend/Dockerfile` ENV defaults** — add `KRELIX_BIND_HOST=0.0.0.0`, `KRELIX_BIND_PORT=8000`. `DATABASE_URL`, `REDIS_URL`, `KRELIX_SECRET_KEY` must be supplied at runtime by Compose; no defaults.

9. **Verify locally:**
   - `make dev-services` running
   - `.env` populated with a valid `KRELIX_SECRET_KEY` (≥32 chars)
   - `make dev-backend` starts; `curl localhost:8000/readyz` → `{"status":"ready"}`
   - Stop Redis (`docker compose -f docker-compose.dev.yml stop redis`) → `/readyz` → 503
   - Remove `KRELIX_SECRET_KEY` from `.env` → backend fails to start with a clear Pydantic validation error
   - `make test` passes (integration tests skipped unless `--run-integration` flag or env var set, which keeps CI fast)

## Acceptance Criteria

- [ ] `backend/src/krelix/config.py` exists; `Settings` rejects a missing or <32-char `KRELIX_SECRET_KEY`.
- [ ] `backend/src/krelix/db.py` exposes `init_engine`, `dispose_engine`, `get_db`, `ping_db`.
- [ ] `backend/src/krelix/redis_client.py` exposes `init_redis`, `dispose_redis`, `get_redis`, `ping_redis`.
- [ ] `app` lifespan initializes both connections at startup and disposes them at shutdown.
- [ ] `GET /readyz` returns 200 with `{"status":"ready"}` when DB + Redis reachable.
- [ ] `GET /readyz` returns 503 when either is unreachable.
- [ ] Missing or short `KRELIX_SECRET_KEY` fails startup with a clear error mentioning the variable name.
- [ ] `make test` passes; integration tests can be opted into via a documented flag.
- [ ] `make typecheck` clean (mypy strict on the new modules).

## Out of Scope (for this ticket)

- ORM models — T010
- Migrations — T011
- Any auth — T013–T016
- `get_db` is created but not yet consumed by any router (those land in later phases)
- Connection pool tuning — defaults are fine for v1

## Notes

- `pool_size=5, max_overflow=10` is a sensible single-operator default. v2 metrics work may need tuning; flag in completion summary if you have a strong reason to change.
- `from_url(..., decode_responses=True)` means Redis returns `str` not `bytes` — saves boilerplate everywhere downstream.
- The `text("SELECT 1")` import in `ping_db` is from `sqlalchemy` — don't forget the import in implementation.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
