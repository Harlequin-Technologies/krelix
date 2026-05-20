# T005 — Control-plane Dockerfile + basic FastAPI app (healthz/readyz) + structlog

**Status:** Done
**Phase:** 1 — Project scaffolding and dev environment
**Estimated session length:** 2 hr
**Depends on:** T002
**Blocks:** T007, T008
**Maps to:** `architecture.md` Component 2 (Control Plane: krelix-api + krelix-worker); `deployment.md` "Repository & Container Images" and the `docker-compose.yml` sketch; `auth-and-security.md` (structlog redaction).

---

## Objective

Build the minimum runnable `krelix-control` Docker image: a multi-stage Dockerfile that installs deps with `uv`, runs the FastAPI app via `uvicorn` (entrypoint `krelix-api`) or arq worker via the same image (entrypoint `krelix-worker`). The FastAPI app at this stage has exactly two endpoints: `GET /healthz` and `GET /readyz`. Structlog is configured for JSON output to stdout, with a redaction filter for known secret fields.

## Context

`krelix-control` is a single Docker image with two entrypoints, distinguished by the compose `command` (`krelix-api` vs `krelix-worker`). Multi-stage build keeps the image lean — a builder stage installs deps with uv, the runtime stage copies only the venv + source. The `/healthz` endpoint reports liveness (process up). `/readyz` reports readiness (DB and Redis reachable) — for this ticket, since we don't have a DB connection yet, `/readyz` returns 200 as long as the process is up; later tickets wire real readiness checks.

## Read for context

- [`../03-technical/architecture.md`](../03-technical/architecture.md) — Component 2 detail
- [`../03-technical/deployment.md`](../03-technical/deployment.md) — Dockerfile expectations, compose sketch
- [`../03-technical/auth-and-security.md`](../03-technical/auth-and-security.md) — "Logging and audit" section (structlog redaction expectations)
- [`T002-backend-python-package.md`](T002-backend-python-package.md) — established structlog and dep set

## Files to create

- `backend/Dockerfile` — multi-stage build
- `backend/.dockerignore` — exclude `__pycache__/`, `.venv/`, tests, etc.
- `backend/src/krelix/main.py` — FastAPI app object + `/healthz`, `/readyz` routes
- `backend/src/krelix/logging.py` — structlog config with secret-redaction processor
- `backend/src/krelix/__main__.py` — entrypoint dispatcher (`krelix-api` vs `krelix-worker`)
- `backend/src/krelix/worker.py` — arq WorkerSettings stub (no jobs registered yet, just the shape)
- `backend/tests/test_health.py` — tests `/healthz` and `/readyz` return 200

## Files to modify

- `backend/pyproject.toml` — add `[project.scripts]` entries: `krelix-api = "krelix.__main__:run_api"`, `krelix-worker = "krelix.__main__:run_worker"`

## Files to NOT touch

- `frontend/`, `agent/`, `packaging/` — separate
- Anything under `docs/` or `.claude/`

## Steps

1. **Write `backend/src/krelix/logging.py`** — configure structlog with:
   - JSON renderer for production (stdout)
   - Timestamps in ISO format, UTC
   - A processor that redacts known secret field names: `password`, `password_hash`, `token`, `hf_token`, `secret_key`, `authorization`, `cookie`, `set-cookie`. The processor walks the event dict and replaces any matching key's value with `"<redacted>"`.
   - Expose `configure_logging()` callable that's idempotent.

2. **Write `backend/src/krelix/main.py`:**
   ```python
   from fastapi import FastAPI
   from .logging import configure_logging

   def create_app() -> FastAPI:
       configure_logging()
       app = FastAPI(title="Krelix Control Plane", version="0.0.1")

       @app.get("/healthz")
       async def healthz() -> dict[str, str]:
           return {"status": "ok"}

       @app.get("/readyz")
       async def readyz() -> dict[str, str]:
           # TODO(T009): wire real DB + Redis readiness checks
           return {"status": "ready"}

       return app

   app = create_app()
   ```

3. **Write `backend/src/krelix/__main__.py`** — small dispatcher exposing `run_api()` (calls `uvicorn.run("krelix.main:app", ...)`) and `run_worker()` (calls `arq.run_worker(WorkerSettings)`). Read host/port from env vars (`KRELIX_BIND_HOST`, default `0.0.0.0`; `KRELIX_BIND_PORT`, default `8000`).

4. **Write `backend/src/krelix/worker.py`** — minimal `WorkerSettings` class with empty `functions: list = []`. Reads `redis_settings` from env (`REDIS_URL`). Don't register any jobs yet.

5. **Update `backend/pyproject.toml`** to expose the two scripts:
   ```toml
   [project.scripts]
   krelix-api = "krelix.__main__:run_api"
   krelix-worker = "krelix.__main__:run_worker"
   ```

6. **Write `backend/tests/test_health.py`:**
   ```python
   import pytest
   from httpx import ASGITransport, AsyncClient

   from krelix.main import app

   @pytest.mark.asyncio
   async def test_healthz() -> None:
       async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
           r = await client.get("/healthz")
           assert r.status_code == 200
           assert r.json() == {"status": "ok"}

   @pytest.mark.asyncio
   async def test_readyz() -> None:
       async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
           r = await client.get("/readyz")
           assert r.status_code == 200
   ```

7. **Write `backend/Dockerfile`** — multi-stage:
   ```dockerfile
   # syntax=docker/dockerfile:1.7

   FROM python:3.12-slim-bookworm AS builder
   ENV UV_VERSION=0.5.x
   RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
   ADD --chmod=755 https://astral.sh/uv/install.sh /uv-installer.sh
   RUN /uv-installer.sh && mv /root/.local/bin/uv /usr/local/bin/uv
   WORKDIR /app
   COPY pyproject.toml uv.lock ./
   COPY src ./src
   RUN uv sync --frozen --no-dev

   FROM python:3.12-slim-bookworm AS runtime
   ENV PATH="/app/.venv/bin:$PATH" \
       PYTHONUNBUFFERED=1 \
       PYTHONDONTWRITEBYTECODE=1
   RUN useradd --create-home --uid 1000 krelix
   WORKDIR /app
   COPY --from=builder --chown=krelix:krelix /app /app
   USER krelix
   EXPOSE 8000
   CMD ["krelix-api"]
   ```
   (Pin `UV_VERSION` to a specific recent version when implementing — the `x` above is a placeholder for the agent to fill with the current uv version at build time.)

8. **Write `backend/.dockerignore`:**
   ```
   __pycache__/
   *.py[cod]
   .venv/
   .pytest_cache/
   .mypy_cache/
   .ruff_cache/
   tests/
   .env
   .env.*
   *.log
   ```

9. **Verify locally:**
   - `cd backend && uv run pytest` green (2 tests now)
   - `cd backend && docker build -t krelix-control:dev .` succeeds
   - `docker run --rm -p 8000:8000 krelix-control:dev` starts; `curl http://localhost:8000/healthz` returns `{"status":"ok"}`; `/readyz` returns 200
   - `docker run --rm krelix-control:dev krelix-worker` starts an arq worker that idles (no jobs registered)
   - Logs are JSON to stdout; no secret-shaped fields appear in logs

## Acceptance Criteria

- [ ] `backend/Dockerfile` builds a `krelix-control:dev` image successfully (no warnings about secrets in layers).
- [ ] `docker run -p 8000:8000 krelix-control:dev` runs `krelix-api`; `curl localhost:8000/healthz` → `{"status":"ok"}`.
- [ ] `curl localhost:8000/readyz` → 200.
- [ ] `docker run krelix-control:dev krelix-worker` runs an arq worker without exiting (it idles, waiting for jobs).
- [ ] Logs emitted by the running container are valid JSON, one event per line, UTC ISO timestamps.
- [ ] `backend/tests/test_health.py` passes (`uv run pytest` reports 3 tests: 1 smoke + 2 health).
- [ ] The structlog redaction processor, when given an event with key `password`, replaces the value with `"<redacted>"` (add a unit test for this in `test_logging.py`).
- [ ] Image runs as non-root user `krelix` (verify with `docker run --rm krelix-control:dev id`).

## Out of Scope (for this ticket)

- Real DB / Redis readiness checks in `/readyz` — that lands when DB connection code lands (Phase 2, around T009)
- Any auth, session, or CSRF middleware — Phase 2
- API routers for endpoints, vaults, deployments, etc. — Phase 2+
- Serving the built React SPA from the FastAPI app — a later ticket adds this once the frontend has actual pages
- Image tagging / pushing to GHCR — T008
- Health check exposure to Docker Compose `healthcheck` directives — T007

## Notes

- The `app = create_app()` module-level invocation is intentional: it gives `uvicorn` a stable import target (`krelix.main:app`) and ensures `configure_logging()` runs once at import time. Don't refactor this to lazy initialization without surfacing it.
- Pin the `uv` version used in the Dockerfile so image builds are reproducible. Verify the current stable uv version at build time and pin it.
- Don't add a healthcheck instruction to the Dockerfile itself — let Compose / Kubernetes / systemd handle that externally.

---

## Completion Summary

- **Files touched:**
  - `backend/Dockerfile` (created)
  - `backend/.dockerignore` (created)
  - `backend/src/krelix/main.py` (created)
  - `backend/src/krelix/logging.py` (created)
  - `backend/src/krelix/worker.py` (created)
  - `backend/src/krelix/__main__.py` (created)
  - `backend/tests/__init__.py` (created)
  - `backend/tests/test_smoke.py` (created)
  - `backend/tests/test_health.py` (created)
  - `backend/tests/test_logging.py` (created)
  - `backend/src/krelix/__init__.py` (modified — sets `__version__`)
  - `backend/src/krelix/py.typed` (created)
  - `backend/README.md` (created)
  - `backend/pyproject.toml` (modified — production+dev deps, project scripts, ruff/mypy/pytest config)
  - `backend/uv.lock` (created)

- **Deviations from the ticket (if any):**
  - **T002 backfill rolled into this ticket.** T002 was committed as a partial WIP (no deps in `pyproject.toml`, no `uv.lock`, no `tests/`, no `__version__` / `py.typed`, empty `README.md`). T005 depends on T002, so the remaining T002 prerequisites were completed in this session. All deps installed are the ones T002 originally enumerated.
  - **`worker.py` registers a single private `_noop` placeholder function** instead of an empty `functions: list = []` as the ticket text in Step 4 suggested. Reason: arq 0.26.3 raises `RuntimeError("at least one function or cron_job must be registered")` if zero functions are configured, which would prevent `docker run krelix-control:dev krelix-worker` from idling — directly contradicting acceptance criterion #4. The placeholder is clearly marked for removal once Phase 4 deployment jobs land.
  - **`uv` version pinned to `0.11.14`** in the Dockerfile (the placeholder `0.5.x` in the ticket was an outdated example). 0.11.14 matches the local toolchain that produced `uv.lock`, so frozen sync is reproducible.
  - **Tests counted 6, not 3.** The ticket's AC line says "1 smoke + 2 health = 3 tests" but a later AC line also requires a redaction unit test in `test_logging.py`. Delivered: 1 smoke + 2 health + 3 redaction = 6.
  - **`configure_logging()` also reroutes stdlib loggers (uvicorn, root) through a single structlog JSON handler.** Without this, uvicorn's startup banner is non-JSON plain text and the "all container logs are valid JSON" AC fails. `uvicorn.run(..., log_config=None)` keeps uvicorn from re-installing its default handlers after the structlog setup.
  - **`tests/**` ruff ignores extended from `S101` to also cover `S105`/`S106`** so fake-credential strings in the redaction tests don't trip the hardcoded-password rule.

- **TODOs left for other tickets:**
  - `TODO(T009)` in `backend/src/krelix/main.py` — wire real DB + Redis readiness checks into `/readyz`.
  - In-code note in `backend/src/krelix/worker.py` to remove the `_noop` placeholder once a real arq job is registered.

- **Commit hashes:**
  - `a86d643` — feat(T002): complete backend python package scaffold (T002 backfill, prerequisite for T005)
  - `ebd24fa` — feat(T005): control-plane Dockerfile + FastAPI healthz/readyz + structlog
  - (this docs amendment commit added in a follow-up)
