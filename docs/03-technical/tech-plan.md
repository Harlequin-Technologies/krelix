# Technical Plan — Krelix

**Version:** 1.0
**Date:** 2026-05-19
**Status:** Ready for work breakdown
**Source:** Synthesized from `docs/02-vision/` and operator preferences captured during technical-architect planning

---

## 1. Summary

**What is being built.** Krelix is a self-hosted control plane for AI model operations in a homelab / multi-GPU environment. v1 collapses the manual, multi-hour lifecycle of *"find a model on HuggingFace → figure out variant/quantization → write a docker-compose → debug startup → copy logs into ChatGPT → tweak config → repeat"* into a single UI flow that gets the operator from intent to a working OpenAI-compatible inference URL in ≤ 30 minutes. The product is a control-plane + per-host-agent system: the **Krelix control plane** (FastAPI + React + Postgres + Redis) owns all UI, state, and orchestration; **Krelix host agents** (one per GPU host, container-mode or systemd-mode) own all model I/O, two-tier storage, GPU introspection, and inference-engine lifecycle. v1 ships vLLM as the only engine; the architecture leaves room for v2 adapters (Ollama, llama.cpp, SGLang, TensorRT-LLM, NVIDIA NIM) without redesign.

**How it is being built.** Python 3.12 backend (FastAPI + SQLAlchemy 2 async + arq workers), TypeScript + React 19 frontend (Vite + Tailwind + ECharts + TanStack Query), PostgreSQL 18 for entity state, Redis 7 for jobs + ephemeral pub/sub. Deployed as a Docker Compose stack to a Debian/Ubuntu VM on the operator's `dell-proxmox` Proxmox node, with the option to install bare-metal via systemd units. Host agents ship as a separate Docker image (container mode) or as a `uv`-managed venv + systemd service (bare-metal mode). CI runs on GitHub Actions; images publish to GHCR. All load-bearing libraries are MIT / BSD / Apache 2.0 / PostgreSQL License — no AGPL, commercial-safe.

---

## 2. Stack at a Glance

| Layer | Pick | Notes |
|-------|------|-------|
| Backend language | Python 3.12 | uv-managed env, pyproject.toml-driven |
| Backend framework | FastAPI (latest stable) | async, WebSocket + SSE, OpenAPI built-in |
| Async job queue | arq + Redis 7 | maintenance-mode upstream — see [`dependencies-and-risks.md`](dependencies-and-risks.md) |
| ORM / migrations | SQLAlchemy 2 (async) + Alembic | |
| Database | PostgreSQL 18 | entity state, JSONB for flexible blobs |
| Frontend | React 19 + Vite + TypeScript + Tailwind | SPA, served by the control-plane API in prod |
| Charts | Apache ECharts + `echarts-for-react` | v2 realtime dashboards (250–500 ms refresh) |
| Server state (FE) | TanStack Query v5 | |
| Realtime transports | WebSocket (status, metrics) + SSE (log tail) | FastAPI-native |
| HF integration | `huggingface_hub` (Python lib) | revision pinning, gated access |
| GPU introspection | `pynvml` | inside the host agent only |
| Docker integration | `docker-py` | container-mode host agent only |
| Password hashing | `pwdlib[argon2]` (Argon2id) | replaces passlib |
| Logging | `structlog` (JSON) | with redaction filter |
| Build tools | `uv` (Python), `pnpm` (JS) | |
| Container registry | GHCR (`ghcr.io/harlequin-technologies/krelix-*`) | two images: `krelix-control`, `krelix-agent` |
| CI | GitHub Actions | `pr.yml`, `main.yml`, `release.yml` |

See [`stack.md`](stack.md) for full rationale and the complete library audit.

---

## 3. System Architecture Summary

Two-tier control plane / host-agent system. The **control plane** runs on a single Docker Compose stack (Postgres + Redis + `krelix-api` + `krelix-worker` processes) on the GPU-less `dell-proxmox` VM and owns all state, UI, orchestration, and operator API. **Host agents** run on each registered GPU host in one of two modes (**container** = Docker container that launches sibling vLLM containers, or **bare-metal** = systemd service that launches vLLM as subprocesses); each agent does all HuggingFace downloads, two-tier model storage (hot NVMe ↔ shared vault — operator-configured with global defaults and per-endpoint overrides), GPU introspection (including MIG-instance detection), inference-engine lifecycle, auto-iteration on common failure modes, and log streaming. Communication is REST commands from the control plane to the agent over the agent-initiated persistent WebSocket; events, status updates, and logs flow back the same way. The control plane performs **no direct model-file I/O and no direct HuggingFace network I/O** — that's strictly the agent's job.

See [`architecture.md`](architecture.md) for the full component breakdown, two-tier flow, eviction model, trust boundaries, and deferred-decisions list.

---

## 4. Build Sequence Recommendation

This is a phasing hint, **not** the work breakdown. The work-breakdown skill (`agent-work-breakdown`) will produce the actual tickets. Phases below assume a single-developer (operator + AI agents) cadence and prioritize foundations early so dependent work can land cleanly.

Phases can overlap where indicated. Each phase should ship a runnable increment (some subset of UI + backend working end-to-end) rather than building horizontally across all layers.

1. **Phase 1 — Project scaffolding and dev environment.** Monorepo layout (`backend/`, `frontend/`, `agent/`, `packaging/`, `docs/`); `uv` + `pyproject.toml`; `pnpm` workspace; Dockerfiles for `krelix-control` and `krelix-agent`; `docker-compose.dev.yml`; `make dev` (or `just`); GitHub Actions PR pipeline; structlog config; basic FastAPI app with `/healthz` and `/readyz`.
2. **Phase 2 — Database foundation + auth.** Alembic setup; initial migration (`0001_initial`) for all entities in [`data-model.md`](data-model.md); seed migration (`0002_seed_defaults`) for `global_settings`; first-run admin setup endpoint (`POST /api/v1/auth/setup`); login/logout with Argon2id via `pwdlib`; Redis-backed sessions; CSRF middleware.
3. **Phase 3 — Vault, settings, HF credential management.** Vault CRUD; global settings CRUD; HF credential encrypted storage (AES-256-GCM keyed by `KRELIX_SECRET_KEY` via HKDF). Minimal UI screens for these three.
4. **Phase 4 — Endpoint registration + agent bootstrap protocol.** Endpoint CRUD with per-endpoint override fields; `agent_registration_token` lifecycle; `POST /api/v1/endpoints` returning one-time plaintext token; `POST /agent/v1/register`; **agent → control plane persistent WebSocket** skeleton (auth, heartbeat only).
5. **Phase 5 — Host agent skeleton (container mode first).** `krelix-agent` Docker image; registration flow; persistent WebSocket connection to control plane; GPU inventory via `pynvml` **including MIG-instance detection**; heartbeat loop; `gpu_resource` rows written by the control plane based on agent reports. Bare-metal/systemd path comes in Phase 12.
6. **Phase 6 — HuggingFace browsing + fit prediction.** `GET /api/v1/hf/search`; model metadata fetch + cache into the `model` table; resolved-revision pinning logic; `GET /api/v1/fit-predictions` (computes against live free-VRAM reported by agents).
7. **Phase 7 — Deployment happy path (no iteration yet).** `POST /api/v1/deployments`; arq worker that orchestrates the deploy: send `deploy` command to agent over WebSocket → agent downloads model from HF to hot tier → agent launches vLLM (sibling container) with a single hand-picked config → agent reports status + inference URL → control plane writes `deployment.status='running'` + `inference_url`. No retries yet; no two-tier yet. UI: deployment list + status.
8. **Phase 8 — Auto-iteration loop.** Agent-side failure-mode catalog (start with: OOM at load, OOM at first inference, max-model-len too high, KV-cache too small, unrecognized quantization flag, missing tokenizer revision); bounded retry budget from resolved config; iteration events streamed back as `deployment_status` frames with `iteration` payload; final config persisted on the `deployment` row. UI surfaces iteration progress.
9. **Phase 9 — Log streaming.** Agent captures vLLM container stdout/stderr; relays as `deployment_log` frames on the stream; control plane fans out to `SSE /api/v1/deployments/{id}/logs`; UI live-tail view (US-M-08).
10. **Phase 10 — Two-tier storage + eviction.** Vault config wiring (resolve per-endpoint vault path, surface to agent); hot ↔ vault flow (download → hot → background copy to vault; vault → hot on subsequent deploys); atomic-rename crash safety for `.partial` files; LRU tracking via `model_artifact.last_used_at`; pin/unpin endpoints; eviction sweep on threshold breach or interval. UI: artifact list per endpoint with pin/eject.
11. **Phase 11 — Frontend polish + deployment-history view.** Refine all UI screens; deployment history (US-S-03) with filters; license-metadata badges (US-S-02); HF revision pinning visible in deployment detail (US-S-01); endpoint resolved-config display; download progress on running downloads (US-C-01); initial-config override on deploy (US-C-02).
12. **Phase 12 — Bare-metal/systemd host agent path.** Subprocess engine launcher (replaces docker-py for this mode); systemd unit + hardening; `KRELIX_AGENT_RUNTIME_MODE=systemd` config; documented bare-metal install runbook for hosts.
13. **Phase 13 — Release prep.** README; install runbooks (control plane container, control plane bare-metal, host agent container, host agent bare-metal); GHCR `:latest` and version tags; `CHANGELOG.md`; the hand-curated 20-combo fit-prediction test set defined and run; success criteria measured and recorded.

**Parallelizable work:** Frontend skeleton + page shells can start in parallel with Phase 4–5 backend work. The hand-curated fit-prediction test set is operator work, not agent work — it should be defined no later than the start of Phase 11 so it can be exercised end-to-end before release.

---

## 5. Open Questions Carried Forward

Items that have not been fully resolved by this plan and need answers during the build, or that are deliberately deferred to a later release. The work-breakdown phase should be aware of each one.

### Resolved or substantially answered during planning

- ~~Docker host integration architecture~~ → resolved. Docker API directly in container mode; subprocess in bare-metal mode. No Portainer API integration.
- ~~GPU resource introspection cadence~~ → resolved. Heartbeat at ~30 s plus on-demand on deployment events; live VRAM/util pushed via WebSocket per `gpu_state` frame.
- ~~v1 auth/security posture~~ → resolved. Single admin + session cookies + CSRF + Argon2id + Redis-backed sessions + per-agent bearer tokens. Enterprise stack deferred to commercial product.
- ~~Sandboxing for risky operations~~ → resolved. `--trust-remote-code` OFF by default with explicit per-deployment opt-in path; conversion scripts not executed in v1; systemd unit hardening in bare-metal mode; no `--privileged` containers.
- ~~License capture policy~~ → resolved. Warn-and-proceed in v1; commercial product enforces.
- ~~Immutable revision pinning UX~~ → resolved. Transparent to the operator — Krelix resolves `main` to a commit at deploy time and records it. Operator can optionally override `model_revision`.
- ~~Cloud GPU endpoint support~~ → dropped from v1, parked. Re-scoping is a v1.x/v2 task.

### Open and needing implementation answer

- **Auto-iteration failure-mode catalog (depth).** Phase 8 starts with a known minimal catalog; the catalog grows over the v1 build as real failures show up. By v1 ship, the catalog should cover at minimum the items listed in `architecture.md` "Decisions Deferred to Implementation"; the operator should document new failure patterns as they occur for future expansion.
- **Auto-iteration retry budget default.** Seeded at 5 in `global_settings`; the right number is empirical. Adjust during Phase 8 based on what produces ≥ 30-min time-to-endpoint on the canonical demo.
- **WebSocket frame encoding.** JSON-over-WebSocket initially. If profile data in v2 shows JSON parsing as a bottleneck at 250–500 ms refresh, evaluate msgpack as a swap-in.
- **vLLM engine version pin granularity.** Whether to pin to exact patch (`vllm==0.21.0`) or floating-minor (`vllm>=0.21,<0.22`) for v1's engine container/venv. Pick during Phase 7. Pinning exact patch is safer; floating-minor lets bug-fix releases land without intervention.
- **Eviction-sweep cadence.** Periodic (every 5 min) plus event-driven (after every download/copy that crosses threshold) is the planned default. Confirm during Phase 10 with real workload.
- **Hand-curated 20-combo fit-prediction test set.** The operator defines this list during Phase 11. Phase 13 measures accuracy against it.
- **Engine adapter abstraction surface.** v1 implements only the `VLLMAdapter`, but the `EngineAdapter` protocol it conforms to must be designed cleanly enough that adding Ollama / llama.cpp / SGLang in v2 doesn't require rewriting Krelix. Design pressure during Phases 7–8.

### Explicitly deferred to v1.x / v2

- **Automatic MIG profile management** — v1 detects only. v1.x or v2 adds profile-change-as-side-effect-of-deployment.
- **Cloud GPU endpoint integrations** (RunPod, Modal, Lambda, vast.ai, AWS, GCP, plus the "VM with GPU passthrough" pattern that may need zero special integration).
- **Phase C (benchmark capture + known-good config registry)**, **Phase C+ (exhaustive optimal-config sweep)**, **Phase D (holistic monitoring / livelook)**, **Phase E (agentic orchestration)**.
- **Additional engine adapters** (Ollama, llama.cpp, SGLang, TensorRT-LLM, NIM).
- **Cross-mode combinations** (container agent + subprocess engine, or bare-metal agent + container engine) — v1 couples the two.
- **Adoption-feedback loop / external user validation.** v1 ships "quietly public"; broader validation happens once something is demonstrable.
- **Multi-user / RBAC / audit logs** — the licensed commercial product, not v1 OSS.
- **Built-in TLS / Let's Encrypt** — operator's reverse proxy handles this in v1.
- **Full enterprise auth stack** (Keycloak + OPA + Vault + SPIFFE) — commercial product.

---

## 6. Assumptions Made During Planning

Each of these was a non-obvious call I made while drafting the plan. The work-breakdown phase and the agents building the product should validate each one as it becomes load-bearing.

1. **The operator's existing Proxmox + Docker + Portainer setup is in working order**, GPU passthrough is operational on the Docker host VMs, the NVIDIA Container Toolkit is installed and verified (`docker run --gpus all nvidia/cuda:... nvidia-smi` works), and CUDA drivers on the host are compatible with the vLLM image's CUDA expectations. v1 builds on top of this — Krelix does NOT manage Proxmox VMs, GPU passthrough, or driver/toolkit installs.
2. **The `dell-proxmox` GPU-less node is the natural home for the Krelix control plane VM.** 32 GB RAM and a 256 GB NVMe boot drive are more than enough for FastAPI + Postgres + Redis + a small frontend bundle. If a different control-plane host is preferred, the only difference is which VM gets the compose stack.
3. **A bounded retry budget (~5) over a small failure-mode catalog is enough to make ≥ 30-minute time-to-endpoint feasible** for the canonical MVD demo and other "normal" model deploys. Novel models may still fail to converge; that's accepted and surfaced cleanly to the operator (logs + final config).
4. **vLLM is the right primary engine to ship in v1.** Confirmation comes empirically during Phase 7–8 once the adapter is implemented and engine-abstraction surface area is visible. If vLLM proves a poor fit, the architecture's `EngineAdapter` design lets us swap to another engine without breaking the control plane.
5. **A single-operator security model — local admin user, encrypted HF token, no multi-user auth — is acceptable for v1 OSS.** Enterprise auth lands in the eventual commercial product. Code shape leaves room for RBAC retrofit (single `current_admin_user` dependency).
6. **JSON-over-WebSocket is fast enough for v2's 250–500 ms metric refresh.** If profile data later shows otherwise, msgpack is a tractable swap.
7. **Other multi-GPU homelab operators experience pain similar enough to the operator's that they would adopt Krelix once available.** Unvalidated; supported by observed-but-not-interviewed behavior. v1 still delivers operator value if this assumption is wrong.
8. **The shared-vault topology (one vault NFS-mounted on multiple hosts) is what the operator will end up with** for cross-host model dedup. Per-host vault is supported by the same configuration mechanism, but the operator has indicated shared as the preferred direction.
9. **NVIDIA-only.** v1 hardware support is NVIDIA via NVML + the NVIDIA Container Toolkit. AMD ROCm, Apple Silicon, and Intel GPUs are not in scope. (Future engine adapters could introduce non-NVIDIA paths without changing the control plane's data model.)
10. **Library versions chosen against current state (as of May 2026), not training-data defaults.** Verified during planning: PostgreSQL 18 stable, React 19 production-ready, vLLM 0.21.x supports Python 3.10–3.14, arq in maintenance-only mode (kept anyway with documented migration path), `passlib` replaced by `pwdlib` (Argon2id) because passlib breaks on Python 3.13+.

---

## 7. User-Required Decisions and Actions

Things the operator must do or decide that an AI coding agent cannot. Consolidated from `deployment.md`. The work-breakdown skill should NOT generate tickets that try to automate these.

### One-time / installation

- **Generate and durably store `KRELIX_SECRET_KEY`** (32+ random bytes, base64url-encoded). Keep a backup separate from the host — losing this means losing the encrypted HF token.
- **Generate `POSTGRES_PASSWORD` and `REDIS_PASSWORD`** for the compose stack.
- **Create the control-plane VM** on the chosen host (Debian/Ubuntu LTS, Docker + Compose installed, 8 GB+ RAM, 40 GB+ disk).
- **Set up internal DNS** for the control plane (e.g., `krelix.dropthe8.com → 10.x.x.x`).
- **(Optional) Configure TLS** by pointing the operator's existing nginx-proxy-manager at the control-plane VM's port 8000.

### Per-GPU-host setup

- **Decide host agent mode** (container or bare-metal/systemd) for each GPU host.
- **Confirm GPU passthrough + NVIDIA driver + (container mode only) NVIDIA Container Toolkit** are working on the host.
- **For bare-metal mode:** pre-install vLLM in a dedicated venv (e.g., `/opt/krelix/engines/vllm/`) using `uv` + pinned Python; record its Python executable path for the agent config.
- **Create the hot-tier directory** (default `/var/lib/krelix/hot`) with sufficient NVMe space and correct ownership for the agent's runtime user.
- **(If using a shared vault) pre-mount the vault filesystem** at the agreed mount path (NFS mount from the vault server, etc.).
- **(If using MIG)** configure MIG profiles externally via `nvidia-smi mig -i <idx> -cgi <profiles>` — v1 detects only, does not change profiles.

### Per-endpoint registration

- **Register the endpoint** in the Krelix UI to receive a one-time bootstrap token.
- **Paste the token** into the agent's config and start the agent (Docker Compose for container mode; `systemctl start krelix-agent` for bare-metal).

### Ongoing operator decisions

- **Enter the HuggingFace token** once via the UI after first login.
- **Accept HF per-model gate approvals** on the HuggingFace website for any gated model the operator wants to use.
- **Pin models** in the UI when the operator wants them protected from auto-eviction.
- **Define the hand-curated 20-combo fit-prediction test set** before v1 release (Phase 11 / 13).
- **(If wanted)** put the existing reverse proxy in front of Krelix for TLS.

---

## 8. Pointers

- [`stack.md`](stack.md) — full stack decisions with rationale and library audit
- [`architecture.md`](architecture.md) — components, two-tier flow, eviction, trust boundaries, deferred decisions
- [`data-model.md`](data-model.md) — entities, fields, indexes, migrations, seed data
- [`api-contracts.md`](api-contracts.md) — operator API (`/api/v1`) and agent protocol (`/agent/v1`); story-to-endpoint traceability table
- [`auth-and-security.md`](auth-and-security.md) — auth, secrets, threat model, TLS strategy
- [`deployment.md`](deployment.md) — install paths (control-plane + agent, container + bare-metal), CI/CD, monitoring, backup, user-required actions
- [`dependencies-and-risks.md`](dependencies-and-risks.md) — third-party services, key libraries, engineering / operational / process / strategic risks
- Vision artifacts: [`../02-vision/prd.md`](../02-vision/prd.md), [`../02-vision/personas.md`](../02-vision/personas.md), [`../02-vision/user-stories.md`](../02-vision/user-stories.md), [`../02-vision/scope.md`](../02-vision/scope.md), [`../02-vision/success-metrics.md`](../02-vision/success-metrics.md)
- Discovery artifacts: [`../01-discovery/interview-notes.md`](../01-discovery/interview-notes.md), [`../01-discovery/parking-lot.md`](../01-discovery/parking-lot.md), [`../01-discovery/open-questions.md`](../01-discovery/open-questions.md)
