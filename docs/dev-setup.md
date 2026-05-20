# Local Development Setup

This guide walks through setting up a Krelix dev environment on your workstation. Postgres and Redis run in Docker; the application code (backend API, worker, frontend) runs natively under `uv` and `pnpm` so iteration is fast and no rebuild is needed per code change.

## Prerequisites

- **Docker** with the Compose v2 plugin (`docker compose ...`)
- **Python 3.12**
- **[`uv`](https://docs.astral.sh/uv/)** — Python package manager
- **Node.js 20+**
- **[`pnpm`](https://pnpm.io/)** — JS package manager
- **GNU `make`**

## First-time setup

From the repo root:

```bash
# 1. Copy the env template and generate a real secret key.
cp .env.example .env
python -c 'import secrets; print(secrets.token_urlsafe(32))'
# Paste the printed value as KRELIX_SECRET_KEY in .env.

# 2. Install Python deps for backend + agent.
cd backend && uv sync && cd ..
cd agent   && uv sync && cd ..

# 3. Install JS deps for frontend.
cd frontend && pnpm install && cd ..
```

`.env` is gitignored; never commit it.

## Daily workflow

In one terminal, bring up the stateful services:

```bash
make dev-services
```

This boots Postgres 18 + Redis 7 on `127.0.0.1:5432` and `127.0.0.1:6379`. The Make target waits until both containers report healthy.

Then, in three separate terminals, run whichever components you're working on:

```bash
make dev-backend    # FastAPI + auto-reload on http://127.0.0.1:8000
make dev-worker     # arq worker (idles until jobs are registered)
make dev-frontend   # Vite dev server on http://localhost:5173
```

You can also run `make dev` to start services and print the next-step commands.

## Other useful targets

```bash
make help        # list all targets
make lint        # ruff + eslint + prettier across backend/frontend/agent
make typecheck   # mypy + tsc
make test        # pytest + vitest
make build       # build the krelix-control and krelix-agent Docker images
```

## Tear-down

```bash
make dev-down
```

The Postgres and Redis data persist in named Docker volumes (`postgres-dev-data`, `redis-dev-data`). To fully reset:

```bash
docker volume rm krelix-claude-attempt_postgres-dev-data krelix-claude-attempt_redis-dev-data
```

(The volume prefix is the Compose project name, which defaults to the directory name. Check with `docker volume ls`.)

## Notes

- Dev passwords are hardcoded (`krelix_dev`) — they are not used in production. Production secrets are managed via `.env` in the production Compose stack.
- Postgres and Redis bind to `127.0.0.1` only, so they're never exposed beyond the dev workstation.
