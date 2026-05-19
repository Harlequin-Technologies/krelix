# Stack — Krelix

All picks are biased toward (1) constraint-fit, (2) right-sizing for v1, (3) compatibility with the v2/v3 roadmap so we don't rewrite, and (4) agent-friendliness for AI-coded build.

## Language(s)

**Pick:** **Python 3.12** (backend, worker, host agent) + **TypeScript 5.x** (frontend).

**Rationale:** Python is the natural fit for HuggingFace tooling (`huggingface_hub`), vLLM control, NVML/GPU introspection (`pynvml`), and Docker API clients — almost every relevant library is Python-native. TypeScript is non-negotiable for a reactive web UI that must scale to 250–500 ms metric refresh in v2. Both are top-tier for AI-agent code generation.

**Alternatives considered:** Go for the backend (rejected — HF/vLLM ecosystem maturity in Python wins, and v1 isn't bottlenecked by raw throughput).

---

## Backend Framework

**Pick:** **FastAPI** (latest stable, currently 0.115.x).

**Rationale:** First-class async support (needed for streaming logs and metrics), built-in WebSocket support, automatic OpenAPI generation (frees the frontend from contract drift), Pydantic v2 for validation, MIT-licensed, and the most agent-friendly Python web framework today.

**Alternatives considered:** Flask (rejected — async/WebSocket support is awkward); Django (rejected — too heavy for an API-first control plane).

---

## Frontend

**Pick:** **React 19 + Vite + TypeScript**, styled with **Tailwind CSS** (MIT). Charts via **Apache ECharts** (Apache 2.0) using the `echarts-for-react` wrapper. Server state via **TanStack Query (React Query) v5**. Routing via **React Router v7** (in framework or data-mode, agent picks during implementation). Local UI state via plain `useState` / `useReducer`; no Redux.

**Rationale:** React 19 is stable, production-ready as of mid-2026, and the right choice for a new project — its compiler auto-optimizes re-renders and async-handling primitives (Actions, `useActionState`, `useOptimistic`) reduce boilerplate around the long-running Krelix flows (downloads, deployments). React + Vite is the most prevalent stack agents handle well, has the mature ecosystem needed for the v2 realtime dashboards, and Vite gives near-instant HMR for development. Tailwind keeps styling close to the markup so agents don't drift across separate CSS files. ECharts handles the realtime gauges + line charts the user wants without performance degradation at sub-second refresh rates (uPlot was the close-call alternative — more performant but more obscure, so worse for agents).

**Form factor:** Single-page application served by FastAPI (in production) or by Vite dev server (in development). No SSR — Krelix is a logged-in operator tool, not a public site.

---

## Database

**Pick:** **PostgreSQL 18** (PostgreSQL License — BSD-style, commercial-safe). PG 18.4 is current stable as of May 2026; PG 17 (17.10) is the also-supported close call.

**Location:** Runs as a sibling container in the Krelix Docker Compose stack, persisting to a named Docker volume. Bare-metal install path: `apt install postgresql-18` (Debian/Ubuntu via the PostgreSQL APT repository), manage via standard `pg_hba.conf` / `systemctl`.

**Rationale:** PostgreSQL is the de facto choice for the entity registry — models, artifacts, deployments, endpoints, deployment-history, fit-prediction cache. It also positions Krelix for the commercial product (multi-tenant, RBAC, audit logs) without a SQLite-to-Postgres migration later. JSONB columns will be used for flexible config blobs (vLLM launch args, hardware profiles) so we don't over-normalize early.

**Alternatives considered:** SQLite (rejected — v1 single-operator could use it, but commercial-product migration pain is real, and PostgreSQL works fine in Docker Compose).

---

## Async Job Queue

**Pick:** **arq** (MIT) backed by **Redis 7** (BSD).

**Rationale:** Model downloads (multi-GB, 5–20 minutes), deployment + auto-iteration loops (5–20 minutes), and v2 benchmarks (longer) are all long-running tasks that must survive a control-plane restart. arq is async-native (clean fit with FastAPI), lightweight, and well-documented; Redis is a tiny extra container, well-understood by agents and operators alike.

**Alternatives considered:** Celery + Redis (heavier, more boilerplate, sync-first); procrastinate (PostgreSQL-backed, removes Redis entirely — close call, but agents handle the arq+Redis pattern better and Redis is also useful for ephemeral state and v2 metrics buffering).

---

## ORM & Migrations

**Pick:** **SQLAlchemy 2.x** (async style) + **Alembic** for migrations.

**Rationale:** The pair is the Python-database default, agent-friendly, and supports both sync (initial scaffolding) and async (request-path queries). Alembic migrations are version-controlled and reversible.

---

## HuggingFace Integration

**Pick:** **`huggingface_hub`** (Apache 2.0) — the official Python client.

**Rationale:** Native search, metadata fetch, revision-pinned downloads, gated-model auth, local cache layout. The PDF's recommendation. Don't reinvent.

---

## GPU Introspection

**Pick:** **`pynvml`** (BSD-3) — the official Python NVML bindings.

**Rationale:** Direct access to per-GPU VRAM, utilization, temperature, power — exactly what fit prediction (v1) and the v2 monitoring dashboards both need. Runs only inside the **host agent** (which is the only component with direct GPU/NVML access).

---

## Docker API Client

**Pick:** **`docker-py`** (Apache 2.0).

**Rationale:** Standard Python Docker client. The host agent uses it to launch and manage vLLM containers as siblings on each Docker host. Speaks directly to `/var/run/docker.sock` mounted into the host-agent container.

---

## Realtime Transport

**Picks:**

- **WebSocket** (FastAPI built-in) for deployment status updates and (v2) live metrics push.
- **Server-Sent Events (SSE)** for the live log tail (US-M-08).

**Rationale:** SSE is the simplest pattern for unidirectional streaming (logs flow one way). WebSocket is needed where bidirectional control is useful and where 250–500 ms metrics push (v2) demands lower overhead than HTTP polling. Both are FastAPI-native, no extra library.

---

## Key Libraries (consolidated)

| Library | Purpose | License | Why this one |
|---------|---------|---------|--------------|
| `fastapi` | Backend HTTP + WS framework | MIT | Async-first, OpenAPI built-in, agent-friendly |
| `uvicorn[standard]` | ASGI server | BSD-3 | Standard FastAPI server |
| `pydantic` v2 | Request/response validation | MIT | Bundled with FastAPI |
| `sqlalchemy[asyncio]` v2 | ORM | MIT | De facto Python ORM |
| `alembic` | Migrations | MIT | SQLAlchemy-native |
| `asyncpg` | PostgreSQL driver | Apache 2.0 | Fastest async Postgres driver |
| `arq` | Async job queue | MIT | Async-native, Redis-backed |
| `redis-py` | Redis client | MIT | Standard |
| `huggingface_hub` | HF Hub API + downloads | Apache 2.0 | Official |
| `docker` (docker-py) | Docker API client | Apache 2.0 | Standard |
| `pynvml` | NVIDIA NVML bindings | BSD-3 | Direct GPU introspection |
| `httpx` | HTTP client | BSD-3 | Async-first, used for inter-service calls |
| `pwdlib[argon2]` | Password hashing for admin login | MIT | Modern replacement for passlib (which broke on Python 3.13). Argon2 backend via `argon2-cffi`. |
| `python-jose[cryptography]` | Session token signing | MIT | Standard |
| `structlog` | Structured logging | Apache 2.0 / MIT | JSON logs, agent-readable |
| **Frontend:** | | | |
| `react` + `react-dom` | UI framework | MIT | Standard |
| `vite` | Dev server + build | MIT | Fast HMR |
| `typescript` | Type system | Apache 2.0 | Standard |
| `tailwindcss` | Styling | MIT | Agent-friendly utility classes |
| `@tanstack/react-query` | Server state | MIT | Standard |
| `react-router-dom` v6 | Routing | MIT | Standard |
| `echarts` + `echarts-for-react` | Charts + gauges | Apache 2.0 | Performant at sub-second refresh |
| `zod` | Frontend schema validation | MIT | Pairs with TypeScript |

**License audit:** All entries above are MIT, BSD, Apache 2.0, or PostgreSQL License. No AGPL, no GPL, no proprietary licenses. Safe to commercialize.

---

## Build / Package Management

**Backend pick:** **`uv`** (Apache 2.0 / MIT, from Astral) for Python dependency management and virtualenvs.

**Rationale:** Significantly faster than pip; lockfile-first; replaces pip + pip-tools + virtualenv in one tool. Modern and well-supported.

**Frontend pick:** **`pnpm`** (MIT).

**Rationale:** Fast, disk-efficient (content-addressable store), strict node_modules layout that catches phantom dependencies. npm would also work — pnpm is a strict upgrade.

---

## Local Development

The user develops on a workstation with the Krelix repo checked out. A `docker-compose.dev.yml` brings up PostgreSQL and Redis as background services on the dev workstation. The FastAPI backend runs via `uv run uvicorn ... --reload` for hot reload; the React frontend runs via `pnpm dev` (Vite) on port 5173 with proxying to the backend on port 8000.

For testing against real GPU endpoints, the developer points the local Krelix instance at one of the homelab Docker hosts (running the Krelix host agent), or runs the host agent locally for a fully self-contained loopback dev environment.

A single `make dev` (or `just dev` if `just` is preferred) target brings everything up. Specific Makefile targets and developer-runbook detail are deferred to implementation.

---

## Decisions deferred to implementation

These are at the library/utility level and don't need to be locked at this layer:

- Specific Tailwind theming / design tokens
- Specific React component library (Headless UI vs. Radix vs. roll-our-own primitives) — agents can pick during build
- Specific testing libraries (pytest is implied for Python; Vitest for frontend) — exact assertion-library style left open
- Specific structured-logging fields beyond a basic schema
