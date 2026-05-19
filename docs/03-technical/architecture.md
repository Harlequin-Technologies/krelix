# Architecture — Krelix

## System Overview

Krelix is a **control-plane / host-agent** system. The **Krelix control plane** is a single Python (FastAPI) application plus its supporting datastores (PostgreSQL + Redis), running on the `dell-proxmox` node. It owns all state, all UI, all orchestration logic, and all operator-facing API surface. **It performs no direct model-file I/O and no direct HuggingFace network I/O.**

A **Krelix host agent** runs on each registered GPU host (`epyc-proxmox`, `ripper-proxmox`, and any other GPU host the operator registers). The host agent supports two installation modes — both first-class in v1, **mutually exclusive per host**:

- **Container mode:** Agent runs as a Docker container on the host. Launches inference engines (vLLM in v1) as **sibling Docker containers** via the local Docker socket.
- **Bare-metal mode:** Agent runs as a **systemd service** on the host. Launches inference engines as **local subprocesses** via CLI (operator pre-installs the engine — e.g., vLLM in a venv — and gives the agent its path).

Independent of mode, the host agent is the I/O actor for its host: it downloads models from HuggingFace, manages the two-tier model storage (hot NVMe ↔ vault), introspects GPU state via NVML, launches and supervises inference engine processes, runs the auto-iteration loop on deployment failures, and streams logs (v1) and metrics (v2) back to the control plane.

This architecture mirrors well-trodden patterns (Kubernetes apiserver ↔ kubelet, Salt master ↔ minion): the control plane is small, stateful, and centralized; the agents are stateless-from-the-control-plane's-perspective, do the heavy lifting, and report back. It scales linearly with the number of registered GPU hosts and survives a control-plane restart without losing in-flight downloads on the agents.

## Components

### 1. Web UI (React SPA)

- **Responsibility:** Operator-facing UI for endpoint registration, HF browsing, fit prediction, deployment trigger, deployment status, log viewing, eject, vault/settings management. v2 adds the realtime metrics dashboards.
- **Talks to:** Krelix control plane only — REST + WebSocket + SSE. Never talks to the host agents directly.
- **Does not:** Hold any persistent state. Reload-and-recover state from the control-plane API on every refresh.

### 2. Krelix Control Plane (FastAPI + arq workers)

- **Responsibility:** Owns the system's source of truth (PostgreSQL), serves the web UI (built React SPA assets and the JSON API), orchestrates all multi-step workflows (deploy, eject, fit-prediction, eviction-policy distribution) via arq-backed jobs, terminates the agent-side persistent WebSocket connections for log/metric streams and fans them out to UI clients.
- **Talks to:**
  - PostgreSQL (entity state) — asyncpg.
  - Redis (job queue + pub/sub channel for log/metric fan-out) — redis-py.
  - Host agents (over HTTPS+token) — outbound REST for commands. Inbound WebSocket from agents for streams.
  - Web UI — outbound to clients via WebSocket + SSE; inbound REST from clients.
- **Does not:** Download anything from HuggingFace. Touch model files. Talk to Docker sockets. Talk to NVIDIA NVML. Have file storage requirements beyond its own working data and the built frontend assets.

The control plane is split into two processes inside the container:
- `krelix-api` — FastAPI/uvicorn process; handles HTTP, WebSocket, SSE.
- `krelix-worker` — arq worker process; handles long-running async tasks (orchestrating an agent through a deploy, etc.).

Both processes share the same Python codebase and the same PostgreSQL + Redis. The split is process-level, not service-level — they ship in the same Docker image.

### 3. PostgreSQL

- **Responsibility:** All entity state. Endpoints, GPU resources, models (HF metadata cache), model artifacts (per-host inventory of what's where), deployments + history, vaults, configuration (global + per-endpoint overrides), HF credentials (encrypted), admin user(s).
- **Talks to:** Control plane only (both `krelix-api` and `krelix-worker`).
- **Does not:** Hold any binary model data — only references to where artifacts live on which host's hot/vault tier.

### 4. Redis

- **Responsibility:** arq job queue (durable). Pub/sub channels for high-fan-out events (log lines for a given deployment, status transitions). Short-lived caches if useful (e.g., cached HF search results).
- **Talks to:** Control plane only.
- **Does not:** Hold persistent state that matters — Postgres is the source of truth. Redis is replaceable / wipeable.

### 5. Krelix Host Agent (one per GPU host)

- **Responsibility:** All host-local I/O and lifecycle work for its GPU host. Specifically:
  - GPU inventory & live VRAM/utilization (via `pynvml`), **including detection of MIG-capable GPUs and any operator-configured MIG instances** — each active MIG instance reported as its own `gpu_resource`. v1 does NOT manage MIG profiles itself.
  - HuggingFace downloads (via `huggingface_hub`) to the configured hot tier.
  - Two-tier storage management (hot ↔ vault — see "Two-tier model storage" below).
  - vLLM container lifecycle (via `docker-py` against the local `/var/run/docker.sock`).
  - **Auto-iteration loop** on deployment failures (catalog of recoverable errors + adjustments — exact catalog deferred to implementation).
  - Log streaming from a running/failing vLLM container back to the control plane via persistent WebSocket.
  - LRU tracking on hot-tier artifacts and periodic eviction sweeps per configured policy.
  - Heartbeat + health to the control plane.
- **Talks to:**
  - HuggingFace Hub (HTTPS outbound).
  - **In container mode:** local Docker socket (Unix socket mounted into the agent container).
  - **In bare-metal mode:** the local kernel directly via `asyncio.subprocess` to fork/exec engine processes; no Docker dependency.
  - Local NVML (in container mode via mounted `/dev/nvidia*` devices + NVIDIA Container Toolkit; in bare-metal mode via system-installed NVML libraries the agent user has access to).
  - Hot tier (local NVMe path — bind-mounted into the container in container mode; direct filesystem access in bare-metal mode).
  - Vault tier (same — bind-mounted path in container mode; direct filesystem access in bare-metal mode).
  - Control plane: outbound HTTPS+token to register and to fetch its own assigned config; outbound WebSocket-to-the-control-plane to receive commands and to stream logs/metrics back. (The agent initiates the WebSocket so the agent can sit behind a homelab firewall without the control plane needing to "reach back in.")
- **Does not:** Talk to Postgres or Redis directly. Talk to the web UI directly. Talk to other host agents. Own any state the control plane doesn't also know about — agents are recoverable: if an agent is wiped and reinstalled, the control plane can re-sync its assignments and the agent re-reports its hot/vault inventory.

### 6. Inference Engine Processes (managed by the host agent)

- **Responsibility:** Actual model inference. One engine process per deployment. Reads model from the host's hot tier (always — see two-tier flow). Serves an OpenAI-compatible HTTP API on a host-side port assigned by the agent.
- **Form factor (set by the host agent's mode):**
  - **Container mode:** A sibling Docker container the agent launches via the local Docker socket.
  - **Bare-metal mode:** A child subprocess of the agent, fork-execed via `asyncio.subprocess` against the operator-installed engine binary/venv.
- **Talks to:** Hot-tier filesystem (read). Operator/downstream tools (HTTP, OpenAI-compatible API).
- **Does not:** Know about Krelix. Krelix's host agent treats it as a managed black-box engine — same lifecycle model whether it's a container or a subprocess.

### 7. Vaults

- **Responsibility:** Long-term model storage. **Not Krelix infrastructure** — vaults are operator-managed filesystems (a directory on a big NVMe drive, an NFS export, etc.) that the operator has pre-configured and mounted on the relevant host(s). Krelix references vaults by their mount path on each host.
- **Configuration:** Krelix's control plane stores `Vault` entities (name, description, expected mount path on hosts), with the ability to define multiple. Each GPU endpoint is assigned to exactly one vault. Both **hot-tier path** and **assigned vault** support a global default with per-endpoint override (see "Configuration model" below).

## Two-Tier Model Storage

Each GPU host has two storage locations the host agent manages:

- **Hot tier:** Local NVMe path on the host (e.g., `/var/lib/krelix/hot` on `epyc-proxmox`, on its 8 TB NVMe data drive). vLLM always reads models from here. Limited capacity → subject to eviction.
- **Vault tier:** A mount path on the host (could be a local directory or an NFS mount). Long-term storage for any model that has been downloaded for this host's vault assignment. Larger, possibly slower than hot.

Per the user requirement, **multiple vaults can be defined** in Krelix and assigned per-host. Two GPU hosts in different network segments can be assigned to different vaults (e.g., one local-NVMe vault, one shared NFS vault) without code changes — purely configuration.

### Deployment flow (model storage)

```
1. Operator: deploy model M to endpoint E.
2. Host agent on E checks: is M in hot tier?
     Yes → go to step 5.
3. Host agent checks: is M in E's assigned vault?
     Yes → copy vault→hot. Go to step 5.
4. Host agent downloads M from HuggingFace → hot tier (via huggingface_hub,
   streaming progress to control plane via WebSocket).
   Once download is complete, the agent ALSO kicks off a background task
   to copy hot→vault for long-term storage.
5. vLLM container is started against the hot-tier copy of M.
6. vLLM startup is monitored by the host agent; on failure, auto-iteration
   loop adjusts config and retries within a bounded retry budget.
7. On success: agent reports the vLLM container's inference URL to the
   control plane, which marks the Deployment row as running.
```

### Eviction flow (hot tier)

- **Manual:** Operator ejects a deployment from the UI (US-M-09). Host agent stops the vLLM container. Hot-tier model artifact is **not** immediately deleted — it stays in hot until evicted by the policy. (This preserves "redeploy this same model quickly" performance.)
- **Automatic:** Per-endpoint (or global-default) policy specifies either a **percent free space** threshold or an **absolute free space** threshold on the hot tier. Host agent periodically (and on threshold-triggered events) evaluates: list non-pinned, non-active models in hot tier sorted by `last_used_at` ascending → delete oldest first until threshold satisfied.
- **Pinning:** Models can be marked `pinned` (per-endpoint, by operator). Pinned models are never auto-evicted — only manually. Pin state is stored on the per-endpoint model-artifact record.
- **Active models are never auto-evicted.** An "active" model is one currently loaded by a running vLLM container on the same host.

## Configuration Model (Globals + Overrides)

Per the user's requirement, Krelix supports **uniform global settings with per-endpoint overrides** for:

| Setting | Global default | Per-endpoint override |
|---------|----------------|----------------------|
| Hot-tier path | yes | yes |
| Assigned vault | yes | yes |
| Eviction policy type (`percent_free` / `absolute_free`) | yes | yes |
| Eviction threshold (number) | yes | yes |
| Auto-iteration retry budget | yes | yes |

The resolution rule is simple: **endpoint-level value if set; otherwise global default**. The control plane resolves at command-issue time and pushes the resolved config to the host agent — the agent does not reason about globals vs. overrides; it just gets the resolved settings.

## Data Flow Examples

### Example A — First-time deploy of `Qwen2.5-14B-Instruct-AWQ` to RTX A4000

1. Operator searches "qwen" in the Krelix UI. UI hits `GET /api/v1/hf/search?q=qwen`. Control plane queries `huggingface_hub` (server-side) and caches results in Postgres.
2. Operator drills into `Qwen2.5-14B-Instruct-AWQ`, sees fit prediction against each registered endpoint. For the A4000, prediction = "fits comfortably."
3. Operator clicks Deploy. UI POSTs `/api/v1/deployments`. Control plane creates a `Deployment` row (status=`pending`), enqueues an arq job `orchestrate_deployment(deployment_id)`.
4. The arq worker picks up the job. It resolves the endpoint's config (hot path, vault, retry budget) and sends `POST /commands/deploy` to the host agent on `epyc-proxmox` via the established WebSocket command channel (or HTTP fallback). Status: `provisioning`.
5. Host agent: model not in hot, not in vault. Downloads from HF to hot. Streams progress events → control plane via WebSocket → fanned to UI via the UI's WebSocket. Status: `downloading`.
6. Download complete. Host agent forks a background copy hot → vault.
7. Host agent picks initial vLLM args (e.g., `--quantization awq --max-model-len <reasonable default for VRAM>`) and starts the container via Docker. Status: `starting`. Logs stream agent → control plane via SSE/WebSocket.
8. Suppose initial start fails with OOM. Agent's auto-iteration logic recognizes the failure pattern, reduces `--max-model-len` (or `--gpu-memory-utilization`), retries.
9. Second attempt succeeds. Agent reports inference URL (`http://epyc-proxmox.dropthe8.com:<port>/v1`). Control plane updates `Deployment` row: status=`running`, inference_url=..., final_config=....
10. UI sees status change via WebSocket, renders running deployment with copy-URL button. Wall-clock total ≤ 30 minutes.

### Example B — Eject + later redeploy of the same model

1. Operator ejects deployment in UI. Control plane sends `POST /commands/stop` to agent. Agent stops + removes the vLLM container. Model artifact remains in hot tier. Status: `stopped`.
2. Later: operator redeploys same model to same endpoint. Host agent finds model in hot tier (already there) and skips both download and vault-copy. Time-to-endpoint: minutes, not 30. (Reproducibility is preserved by the resolved-revision pin from US-S-01.)

### Example C — Auto-eviction on hot tier

1. Threshold for `epyc-proxmox` is configured: `percent_free`, 15%.
2. Operator deploys a third large model. Download starts. Hot tier free space crosses below 15%.
3. Host agent kicks an eviction sweep: lists hot-tier models, filters out active and pinned, sorts by `last_used_at` ascending.
4. Deletes the LRU model. Frees space. Continues download. Reports eviction event to control plane (visible in deployment-history UI).

## Trust Boundaries

- **Untrusted input enters at:**
  - Operator inputs in the web UI (validated server-side via Pydantic).
  - HuggingFace model artifacts (third-party — see auth-and-security.md for the `trust_remote_code` posture and conversion-script handling).
  - vLLM container internals (treated as third-party; control plane and agent only manage lifecycle, not internal behavior).
- **Trusted internal:**
  - Control plane ↔ host agent traffic, authenticated by a per-agent registration token (see auth-and-security.md). Token-bearing requests are trusted.
- **Critically untrusted-but-must-execute:**
  - vLLM containers run with GPU access on the GPU host — they are necessarily privileged within the container. They run **only** with the host agent's own user-id and namespace; the agent does not pass `--privileged` unless explicitly required by an engine. The agent host is itself the trust boundary for "running model code with hardware access."

## Decisions Deferred to Implementation

These are intentionally not nailed down at the architecture layer — agents have latitude during build:

- **Internal class structure within each component** (e.g., how the host agent organizes its modules, how the control plane lays out its FastAPI routers internally).
- **Exact failure-mode catalog for the auto-iteration loop.** v1 must implement at least: OOM at load, OOM at first inference, `--max-model-len` greater than KV-cache-can-support, unrecognized quantization flag, missing tokenizer revision. The full catalog will be refined during build as the operator encounters real failures. (Open question carried forward.)
- **Exact WebSocket framing protocol** between control plane and host agents (JSON-over-WebSocket vs. msgpack vs. JSON-RPC). Default lean: JSON-over-WebSocket with a small envelope `{type, id, payload}` — picked during implementation.
- **Specific React component decomposition** (which UI bits are their own components vs. inlined).
- **Specific eviction-sweep cadence** (event-driven vs. periodic interval) — agent picks during build, with a sensible default of "trigger on every download/copy that crosses threshold + periodic every 5 min."
- **Specific log retention on the agent side** before logs are considered "expired" and dropped from the SSE buffer.
