# Deployment — Krelix

## Target Environment

**Primary production target (v1):**

The **Krelix control plane** runs as a Docker Compose stack on a single VM. Two deployment paths are first-class in v1:

1. **Containerized install (primary, recommended):** Docker Compose stack deployed on a Docker host VM. The operator's reference instance: a Debian/Ubuntu VM on the `dell-proxmox` Proxmox node (no GPU needed for the control plane).
2. **Bare-metal install (also supported, less common):** Direct install on a Debian or Ubuntu VM — Python venv, system-managed Postgres and Redis, systemd units for the API and worker processes.

The **Krelix host agent** supports two installation modes in v1. They are mutually exclusive per host — pick one based on how the operator wants to run inference engines on that host:

- **Container mode (recommended for hosts that already run Docker workloads):** Agent runs as a Docker container; launches inference engines (vLLM in v1) as **sibling Docker containers** via the local Docker socket.
- **Bare-metal mode (for hosts that run inference engines via CLI, no Docker):** Agent runs as a **systemd service**; launches inference engines as **local subprocesses** via CLI. The operator pre-installs vLLM (and future engines) into a known Python environment on the host.

A single GPU host runs only one mode at a time. The cross-combinations (container agent that launches subprocess engines, or bare-metal agent that launches Docker engines) are not in v1 scope.

---

## Environments

- **Local dev:** Developer workstation. `docker-compose.dev.yml` brings up Postgres + Redis as background services. `uv run uvicorn ... --reload` runs the API; `uv run arq krelix_worker.WorkerSettings` runs the worker; `pnpm dev` runs the Vite frontend. Optional: also run the host agent locally and point it at the local control plane for a closed-loop dev environment.
- **Staging:** **None.** v1 is single-operator OSS; the cost of a staging environment outweighs the value at this stage. The user has 40 hrs/week and a single deployment target. Changes ship to production after local dev validation; rollback is a `docker compose pull` to a prior tag.
- **Production:** The operator's homelab — control plane on the dell-proxmox VM, host agents on Docker hosts already running on epyc-proxmox and ripper-proxmox.

---

## Repository & Container Images

- **Source repo:** `github.com/Harlequin-Technologies/krelix`
- **Container registry:** GitHub Container Registry (GHCR) — `ghcr.io/harlequin-technologies/krelix-control:<tag>` and `ghcr.io/harlequin-technologies/krelix-agent:<tag>`. GHCR is free for public images and ties cleanly to the GitHub repo, satisfying the $100 budget.
- **Image layout:** Two Krelix images.
  - `krelix-control` — contains the FastAPI app, the arq worker, the built React SPA assets, and Alembic migration files. Single image, multiple entrypoints (`krelix-api` vs `krelix-worker`).
  - `krelix-agent` — contains the host agent's Python code and entrypoint.
- **Base images:** Both Krelix images derive from a slim Python 3.12 base (e.g., `python:3.12-slim-bookworm`) with `uv` installed in a builder stage. The agent image additionally has the NVIDIA NVML libraries installed at the OS layer (or relies on the NVIDIA Container Toolkit mounting them at runtime — chosen during implementation).

---

## Build & Deploy Process

**Source-to-running flow:**

1. Developer pushes to a feature branch on GitHub.
2. **GitHub Actions** runs the PR pipeline on every PR: lint (`ruff` for Python, `eslint` for TS), type-check (`mypy` and `tsc --noEmit`), unit tests (`pytest`, `vitest`), and a Docker image build (smoke-test only — not pushed).
3. PR is reviewed and merged to `main`.
4. **GitHub Actions** runs the main pipeline: full tests, builds both Docker images, tags with `:edge` (rolling) + `:sha-<short>`, pushes to GHCR.
5. Release: maintainer creates a Git tag `vX.Y.Z`; a separate Actions workflow tags the same image as `:X.Y.Z` and `:latest`.
6. Operator updates production: `docker compose pull && docker compose up -d` on the control-plane VM; for the host agent, the operator re-pulls and restarts the agent container on each GPU host (a one-line shell helper script will be provided in the repo).

**Rollback:** Pull a prior tag and restart. Database migrations are forward-only; rollback expectations are documented per-release in `CHANGELOG.md`. Major destructive migrations are flagged for the operator to take a Postgres backup first.

---

## CI/CD Detail

**CI: GitHub Actions** (free tier covers this comfortably).

Workflows in `.github/workflows/`:

- `pr.yml` — triggered on PR to `main`. Runs:
  - `uv pip install` + `pytest`
  - `pnpm install` + `pnpm test` + `pnpm build`
  - `ruff check .` + `mypy backend/`
  - `pnpm lint` + `tsc --noEmit`
  - `docker build` on both images (no push)
- `main.yml` — triggered on push to `main`. Runs PR pipeline + pushes images tagged `:edge` and `:sha-<short>` to GHCR.
- `release.yml` — triggered on Git tag `v*.*.*`. Re-tags the `:edge` image (or rebuilds at tag) to `:X.Y.Z` and `:latest`.

**No CD-to-production in v1.** The operator pulls and restarts manually. This matches the single-operator deployment posture; automatic deploy-to-prod is premature.

---

## Domain / DNS / TLS

- Krelix is **LAN-only in v1.** No public DNS or public certificate is required for the product to function.
- The operator's existing internal DNS (the `dropthe8.com` domain pointing at homelab hosts) handles name resolution for the control plane and the host agents.
- **TLS is optional.** Operator-supplied reverse proxy (their nginx-proxy-manager instance, Caddy, Traefik, etc.) is the documented path for those who want TLS on the LAN. Krelix sets `Secure` flag on cookies when it sees `X-Forwarded-Proto: https`.
- See [`auth-and-security.md`](auth-and-security.md) "TLS Strategy for v1" for the full posture.

---

## Compose Files (canonical shape)

The repo ships two Compose files:

- `docker-compose.yml` — control plane (control-api, control-worker, postgres, redis).
- `docker-compose.agent.yml` — host agent. Installed separately on each GPU host.

**Control-plane `docker-compose.yml` (sketch):**

```yaml
services:
  postgres:
    image: postgres:18
    restart: unless-stopped
    environment:
      POSTGRES_USER: krelix
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: krelix
    volumes: ["postgres-data:/var/lib/postgresql/data"]

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: ["redis-server", "--requirepass", "${REDIS_PASSWORD}"]
    volumes: ["redis-data:/data"]

  control-api:
    image: ghcr.io/harlequin-technologies/krelix-control:${KRELIX_VERSION:-latest}
    restart: unless-stopped
    depends_on: [postgres, redis]
    environment:
      KRELIX_SECRET_KEY: ${KRELIX_SECRET_KEY}
      DATABASE_URL: postgresql+asyncpg://krelix:${POSTGRES_PASSWORD}@postgres:5432/krelix
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      KRELIX_BIND_HOST: 0.0.0.0
      KRELIX_BIND_PORT: 8000
    ports: ["8000:8000"]
    command: ["krelix-api"]

  control-worker:
    image: ghcr.io/harlequin-technologies/krelix-control:${KRELIX_VERSION:-latest}
    restart: unless-stopped
    depends_on: [postgres, redis]
    environment:
      KRELIX_SECRET_KEY: ${KRELIX_SECRET_KEY}
      DATABASE_URL: postgresql+asyncpg://krelix:${POSTGRES_PASSWORD}@postgres:5432/krelix
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
    command: ["krelix-worker"]

volumes:
  postgres-data:
  redis-data:
```

**Host-agent container-mode `docker-compose.agent.yml` (sketch):**

```yaml
services:
  krelix-agent:
    image: ghcr.io/harlequin-technologies/krelix-agent:${KRELIX_VERSION:-latest}
    restart: unless-stopped
    runtime: nvidia                  # NVIDIA Container Toolkit
    environment:
      KRELIX_CONTROL_URL: https://krelix.dropthe8.com   # or http://krelix.dropthe8.com:8000
      KRELIX_AGENT_TOKEN: ${KRELIX_AGENT_TOKEN}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock        # sibling-container management
      - /var/lib/krelix/hot:/var/lib/krelix/hot          # bind hot tier from host
      - /mnt/krelix-vault:/mnt/krelix-vault              # bind vault mount from host (if used)
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all                                  # NVML access needs all GPUs visible
              capabilities: [gpu]
```

Both files are committed to the repo as authoritative starting points; the operator copies them and fills in env vars.

---

## Bare-Metal Install Path — Control Plane (Debian / Ubuntu)

For the operator's testing scenario (bare-metal install on a Debian/Ubuntu VM):

- **System packages:** `python3.12`, `python3.12-venv`, `uv` (via Astral install script), `postgresql-16`, `redis-server`, `nginx` (optional, as reverse proxy).
- **Database setup:** install PostgreSQL 18 from the official PGDG APT repo (`apt install postgresql-18`); `sudo -u postgres createuser krelix && createdb krelix`; configure password in `.env`.
- **Redis setup:** Edit `/etc/redis/redis.conf` for `requirepass` and `bind 127.0.0.1`.
- **Krelix install:** `git clone` the repo; `uv venv && uv pip install -e .`; `cp .env.example .env` and edit secrets; `uv run alembic upgrade head` to apply migrations.
- **Systemd units (committed in `packaging/systemd/`):**
  - `krelix-api.service` — runs `uv run uvicorn krelix.api:app --host 0.0.0.0 --port 8000`
  - `krelix-worker.service` — runs `uv run arq krelix.worker.WorkerSettings`
- **Frontend assets:** pre-built and shipped in the repo's release artifacts, OR built locally with `pnpm install && pnpm build` and served by Krelix's API process.

Bare-metal install is documented in `docs/install/bare-metal.md` (deferred to implementation — added to the work breakdown).

---

## Bare-Metal Install Path — Host Agent (Debian / Ubuntu)

For hosts where the operator runs inference engines directly via CLI rather than in Docker:

- **System packages:** `python3.12`, `python3.12-venv`, `uv`, NVIDIA driver + CUDA toolkit, and any system libraries the inference engines require.
- **Inference engine pre-install (operator-managed):** The operator installs vLLM in a dedicated Python virtual environment on the host (e.g., `/opt/krelix/engines/vllm/`). The path to the engine's executable is registered via the agent's config. Multiple engine installs can coexist in different venvs for future v2 engine adapters.
- **Krelix agent install:** `git clone` the repo (or pull a release tarball); `uv venv /opt/krelix/agent && uv pip install -e .` (agent subpackage). Configure via `/etc/krelix/agent.env`.
- **Dedicated system user:** Create a `krelix-agent` system user (no login shell). Add to the `video` group (or `render`, depending on driver) for GPU access. Grant ownership of hot-tier and vault paths.
- **Systemd unit (committed in `packaging/systemd/`):** `krelix-agent.service` — runs `uv run krelix-agent` as user `krelix-agent`, restart=on-failure, sane hardening (NoNewPrivileges, ProtectSystem=strict, ReadWritePaths to hot/vault, etc. — see [`auth-and-security.md`](auth-and-security.md)).
- **Inference engine processes** are launched as **child processes of the agent** (not separate systemd units in v1). The agent supervises them directly via `asyncio.subprocess` — capturing stdout/stderr for log streaming, sending SIGTERM/SIGKILL on stop, monitoring exit codes for the auto-iteration loop. If an engine process dies unexpectedly while marked `running`, the agent reports it to the control plane and the deployment transitions to `failed`.

Configuration shape for bare-metal agent (`/etc/krelix/agent.env`):

```
KRELIX_CONTROL_URL=https://krelix.dropthe8.com
KRELIX_AGENT_TOKEN=krelix_agt_...
KRELIX_AGENT_RUNTIME_MODE=systemd
KRELIX_HOT_TIER_PATH=/var/lib/krelix/hot
KRELIX_VAULT_MOUNT_PATH=/mnt/krelix-vault
KRELIX_ENGINE_VLLM_PYTHON=/opt/krelix/engines/vllm/bin/python
KRELIX_ENGINE_VLLM_MODULE=vllm.entrypoints.openai.api_server
```

The agent reports its runtime mode (`docker` or `systemd`) and the engine handles it knows about to the control plane at registration, where they're stored on the `endpoint` row.

Bare-metal host agent install is documented in `docs/install/host-agent-bare-metal.md` (deferred to implementation — added to the work breakdown).

---

## Monitoring & Logs

**v1 monitoring is intentionally minimal:**

- **Application logs:** structlog → JSON to stdout. Captured by Docker's `json-file` driver (or systemd's journal for bare-metal). The operator can `docker compose logs -f control-api` or `journalctl -u krelix-api -f`.
- **Health checks:** Each Krelix service exposes `GET /healthz` (liveness — process is up) and `GET /readyz` (readiness — DB+Redis reachable). Docker Compose `healthcheck` declarations use these.
- **Metrics endpoint:** `GET /metrics` exposed by `control-api` in Prometheus text format, but **no Prometheus instance is shipped in v1.** Operator who wants metrics scraping can point their own Prometheus at it. v2 (D phase) is where Krelix grows real metrics dashboards.
- **Agent health:** Agent's WebSocket heartbeat (`agent_status=online` / `offline`, `last_heartbeat_at`) is the v1 source of truth for "is this host agent alive?" Surfaced in the operator UI's endpoint list.

---

## Backup & Recovery

**What needs backup (operator-managed):**

1. **`KRELIX_SECRET_KEY`** — the root crypto secret. Store the value in a password manager or other persistent location separate from the host. **Losing this means losing the encrypted HF token.** Document this in the install runbook prominently.
2. **PostgreSQL data** — all entity state. Standard `pg_dump` on a schedule (operator's choice; weekly is a sensible default). The compose stack persists Postgres to the `postgres-data` Docker volume.
3. **Model artifacts on vault tier** — operator's responsibility; the vault filesystem is owned by the operator (NFS export, local NVMe, etc.). Krelix can re-download from HF if the vault is wiped, so vault backup is optional.
4. **Hot tier** — ephemeral by design; never needs backup. Eviction logic accepts that it can be re-populated from vault or HF.
5. **Redis data** — only contains the job queue and ephemeral state. Acceptable to lose on restart; v1 does **not** require Redis backups.

**Recovery scenarios:**

- **Control plane VM dies, Postgres volume intact:** restore VM, copy compose files, `docker compose up -d` — Krelix starts from the same state. Agents reconnect to their already-known control plane URL.
- **Postgres volume lost:** restore from `pg_dump` backup. Agents re-register if needed (their token records survive in the backup; if not, regenerate tokens and reinstall agents).
- **`KRELIX_SECRET_KEY` lost:** re-enter HF token via UI; existing sessions invalidated. No other data loss.
- **Host agent host dies:** install agent on replacement host; if replacement preserved the hot tier and vault mounts, artifacts are preserved; otherwise Krelix re-downloads on next deploy.

---

## User-Required Actions

Decisions and actions the operator (not the AI coding agent) must perform during v1 setup or use:

### One-time setup

- **Generate `KRELIX_SECRET_KEY`** (e.g., `python -c 'import secrets; print(secrets.token_urlsafe(32))'`) and store it durably (password manager).
- **Generate `POSTGRES_PASSWORD` and `REDIS_PASSWORD`** for the Compose stack.
- **Create the control-plane VM** on dell-proxmox (or chosen host): Debian/Ubuntu LTS, install Docker + Compose plugin, allocate enough RAM (8GB+ recommended) and disk (40GB+ for the OS + container images + Postgres data).
- **Set up internal DNS** for the control plane host (e.g., `krelix.dropthe8.com → 10.x.x.x`). Krelix doesn't manage DNS.
- **Optional: configure reverse proxy / TLS** via the operator's existing nginx-proxy-manager. Point a hostname at the Krelix VM's port 8000.
- **For each GPU host that will be a Krelix endpoint:**
  - Decide host-agent mode: **container** (engines launched as sibling Docker containers) or **bare-metal/systemd** (engines launched as local subprocesses). One mode per host in v1.
  - Ensure GPU passthrough is working at the Proxmox level (outside Krelix's scope).
  - Ensure `nvidia-smi` reports the GPUs correctly on the host (driver + CUDA toolkit installed).
  - **If container mode:** install the NVIDIA Container Toolkit and verify `docker run --gpus all nvidia/cuda:12.6.0-base nvidia-smi` succeeds.
  - **If bare-metal mode:** pre-install vLLM in a dedicated Python venv on the host (operator's responsibility); record its Python executable path for the agent config.
  - Create the hot-tier directory (default `/var/lib/krelix/hot`) with enough NVMe space, owned by the agent's runtime user.
  - If using a shared vault: pre-mount the vault filesystem at the agreed mount path (e.g., NFS mount from the vault server).
  - If using MIG on a capable GPU: configure MIG profiles externally via `nvidia-smi mig -i <idx> -cgi <profiles>`. Krelix detects what's configured but does not change profiles in v1.

### Per-endpoint registration

- **Register the endpoint** in the Krelix UI to receive a bootstrap token (one-time plaintext).
- **Paste the token** into the agent's `KRELIX_AGENT_TOKEN` env var, then `docker compose -f docker-compose.agent.yml up -d` on the GPU host.

### Per-deployment operator inputs

- **HuggingFace token** entered once via the UI (after first login).
- **HuggingFace per-model gate approvals** done on the HF website by the operator for any gated model they want to use.
- **Optional: pin a model** in the UI to prevent auto-eviction.

### Decisions Krelix asks the operator to make (in UI)

- Global defaults for hot-tier path, default vault, eviction policy and threshold, auto-iteration retry budget.
- Per-endpoint overrides for any of the above.
- Vault definitions (name, mount path).
