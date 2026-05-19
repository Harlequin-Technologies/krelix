# T007 — docker-compose.dev.yml + Makefile dev targets

**Status:** Not started
**Phase:** 1 — Project scaffolding and dev environment
**Estimated session length:** 1.5 hr
**Depends on:** T002, T003, T004
**Blocks:** T008
**Maps to:** `deployment.md` "Compose Files (canonical shape)" and "Local Development"; `tech-plan.md` Section 4 Phase 1.

---

## Objective

Provide a single `make dev` command that brings up a complete local dev environment: PostgreSQL 18 + Redis 7 in containers, backend `krelix-api` running with auto-reload, backend `krelix-worker` running, frontend Vite dev server. Each service is independently restartable. A `.env.example` documents required environment variables.

## Context

Local dev uses Compose for the stateful services (Postgres, Redis) so they're disposable; the application code runs natively on the developer workstation under `uv` / `pnpm` for fast iteration (no rebuild on every code change). The Makefile orchestrates the moving parts. Production Compose files (committed shape from `deployment.md`) come in a later ticket — this is dev-only.

## Read for context

- [`../03-technical/deployment.md`](../03-technical/deployment.md) — "Compose Files (canonical shape)" and "Local Development"
- [`../03-technical/stack.md`](../03-technical/stack.md) — Postgres 18, Redis 7

## Files to create

- `docker-compose.dev.yml` — Postgres + Redis only (the app runs natively for fast iteration)
- `Makefile` — top-level dev orchestration
- `.env.example` — documents required env vars with safe placeholder values
- `docs/dev-setup.md` — short developer onboarding guide

## Files to modify

- Root `README.md` — add a "Local Development" section pointing at `make dev` and `docs/dev-setup.md`
- Root `.gitignore` — ensure `.env` is ignored (should already be from T001; double-check)

## Files to NOT touch

- Production Compose files — those land in a later ticket
- Anything under `backend/`, `frontend/`, `agent/` — their package configs are settled
- `docs/01-discovery/`, `docs/02-vision/`, `docs/03-technical/` — final

## Steps

1. **Write `docker-compose.dev.yml`** with only the stateful services:
   ```yaml
   services:
     postgres:
       image: postgres:18
       container_name: krelix-dev-postgres
       restart: unless-stopped
       environment:
         POSTGRES_USER: krelix
         POSTGRES_PASSWORD: krelix_dev
         POSTGRES_DB: krelix
       ports:
         - "127.0.0.1:5432:5432"
       volumes:
         - postgres-dev-data:/var/lib/postgresql/data
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U krelix"]
         interval: 5s
         timeout: 5s
         retries: 10

     redis:
       image: redis:7-alpine
       container_name: krelix-dev-redis
       restart: unless-stopped
       command: ["redis-server", "--requirepass", "krelix_dev"]
       ports:
         - "127.0.0.1:6379:6379"
       volumes:
         - redis-dev-data:/data
       healthcheck:
         test: ["CMD", "redis-cli", "-a", "krelix_dev", "ping"]
         interval: 5s
         timeout: 3s
         retries: 10

   volumes:
     postgres-dev-data:
     redis-dev-data:
   ```
   Notes:
   - Bind to `127.0.0.1` only (not `0.0.0.0`) so dev DB/Redis aren't exposed beyond the dev workstation.
   - Hardcoded `krelix_dev` passwords are intentional for local dev convenience — they're not used in production.

2. **Write `.env.example`** at the repo root:
   ```
   # Copy to .env and fill in real values for local dev.
   # .env is gitignored.

   # Root crypto secret (32+ random bytes, base64url). Generate with:
   #   python -c 'import secrets; print(secrets.token_urlsafe(32))'
   KRELIX_SECRET_KEY=replace-with-32-byte-random-base64url

   # Database (matches docker-compose.dev.yml defaults)
   DATABASE_URL=postgresql+asyncpg://krelix:krelix_dev@localhost:5432/krelix

   # Redis (matches docker-compose.dev.yml defaults)
   REDIS_URL=redis://:krelix_dev@localhost:6379/0

   # Bind address for krelix-api
   KRELIX_BIND_HOST=127.0.0.1
   KRELIX_BIND_PORT=8000

   # Frontend dev server proxies to this — usually leave default
   ```

3. **Write the `Makefile`** at the repo root:
   ```makefile
   .PHONY: help dev dev-services dev-backend dev-worker dev-frontend dev-down lint typecheck test build

   help:
   	@echo "Targets:"
   	@echo "  make dev           — start everything (services + backend + worker + frontend)"
   	@echo "  make dev-services  — start only Postgres + Redis"
   	@echo "  make dev-backend   — run krelix-api locally with reload"
   	@echo "  make dev-worker    — run krelix-worker locally"
   	@echo "  make dev-frontend  — run Vite dev server"
   	@echo "  make dev-down      — stop services"
   	@echo "  make lint          — run linters across backend + frontend + agent"
   	@echo "  make typecheck     — run type checkers"
   	@echo "  make test          — run all test suites"
   	@echo "  make build         — build Docker images"

   dev: dev-services
   	@echo "Services up. Run in separate terminals:"
   	@echo "  make dev-backend"
   	@echo "  make dev-worker"
   	@echo "  make dev-frontend"

   dev-services:
   	docker compose -f docker-compose.dev.yml up -d
   	@echo "Waiting for postgres + redis healthy..."
   	@until docker compose -f docker-compose.dev.yml ps --format json | grep -q '"Health":"healthy".*"Health":"healthy"'; do sleep 1; done
   	@echo "Services ready."

   dev-backend:
   	cd backend && uv run uvicorn krelix.main:app --reload --host 127.0.0.1 --port 8000

   dev-worker:
   	cd backend && uv run arq krelix.worker.WorkerSettings

   dev-frontend:
   	cd frontend && pnpm dev

   dev-down:
   	docker compose -f docker-compose.dev.yml down

   lint:
   	cd backend && uv run ruff check . && uv run ruff format --check .
   	cd frontend && pnpm lint && pnpm format:check
   	cd agent && uv run ruff check . && uv run ruff format --check .

   typecheck:
   	cd backend && uv run mypy src
   	cd frontend && pnpm typecheck
   	cd agent && uv run mypy src

   test:
   	cd backend && uv run pytest
   	cd frontend && pnpm test
   	cd agent && uv run pytest

   build:
   	docker build -t krelix-control:dev backend/
   	docker build -t krelix-agent:dev agent/
   ```

4. **Write `docs/dev-setup.md`** — short guide:
   - Prerequisites: Docker + Compose plugin, Python 3.12, `uv`, Node 20+, `pnpm`
   - First-time setup: `cp .env.example .env`; edit `.env` with a real `KRELIX_SECRET_KEY`; `cd backend && uv sync`; `cd frontend && pnpm install`; `cd agent && uv sync`
   - Daily workflow: `make dev` then three terminals for backend/worker/frontend; or just `make dev-services` + run whichever component you're working on
   - Tear-down: `make dev-down`; data persists in named volumes — `docker volume rm krelix_postgres-dev-data krelix_redis-dev-data` to fully reset

5. **Update root README** with a `## Local Development` section pointing at `make dev` and `docs/dev-setup.md`.

6. **Verify end-to-end:**
   - `cp .env.example .env && python -c 'import secrets; print(secrets.token_urlsafe(32))' | xargs -I{} sed -i 's|^KRELIX_SECRET_KEY=.*|KRELIX_SECRET_KEY={}|' .env` (or manually edit)
   - `make dev-services` — Postgres + Redis come up healthy
   - In a separate terminal: `make dev-backend` — uvicorn starts, `/healthz` returns 200
   - In a separate terminal: `make dev-worker` — arq worker idles
   - In a separate terminal: `make dev-frontend` — Vite serves on 5173
   - `make lint`, `make typecheck`, `make test` all exit 0
   - `make dev-down` shuts services down cleanly

## Acceptance Criteria

- [ ] `docker-compose.dev.yml` exists and brings up healthy Postgres 18 + Redis 7 containers via `make dev-services`.
- [ ] `.env.example` exists with the documented variables and safe placeholder values.
- [ ] `.env` is gitignored (already covered in T001; verify).
- [ ] `Makefile` has `help`, `dev`, `dev-services`, `dev-backend`, `dev-worker`, `dev-frontend`, `dev-down`, `lint`, `typecheck`, `test`, `build` targets.
- [ ] `make help` lists all targets.
- [ ] `make dev-services` brings up Postgres and Redis; `make dev-down` tears them down.
- [ ] `make dev-backend` starts the FastAPI app with auto-reload at `http://127.0.0.1:8000`; `/healthz` returns 200.
- [ ] `make dev-frontend` starts Vite at `http://localhost:5173` showing the "Krelix" page.
- [ ] `make lint`, `make typecheck`, `make test`, `make build` all exit 0 on a fresh clone after `make dev-services`.
- [ ] `docs/dev-setup.md` exists and describes the workflow end-to-end.

## Out of Scope (for this ticket)

- Production `docker-compose.yml` — that's a later ticket (around release prep)
- The agent's compose file — separate (the agent isn't part of the local dev loop in v1)
- CI workflows — T008
- Database migrations (Alembic) — Phase 2 (T009-era)
- Anything that requires real GPU access locally
- Pre-commit hooks (a "could have" — skip unless requested)

## Notes

- `make` and `docker compose` are POSIX-portable enough for a Debian/Ubuntu dev environment. If you'd prefer `just` over `make`, that's fine — surface the swap before committing. `make` is the safer default agents will know.
- The wait-for-healthy loop in `dev-services` is a basic readiness check; if it's brittle, swap to a simpler `sleep 5`. Don't over-engineer.
- Resist the temptation to add a `dev-all` target that backgrounds backend + worker + frontend in a single command. They produce a lot of log output and benefit from separate terminals.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
