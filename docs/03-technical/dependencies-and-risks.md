# Dependencies and Risks — Krelix

## Third-Party Services

Services Krelix depends on at build time, deploy time, or runtime. None are paid in v1 (within the $100 budget); all have viable fallbacks.

| Service | Purpose | Cost | License / Terms concerns | Alternative if it fails |
|---------|---------|------|--------------------------|------------------------|
| **HuggingFace Hub** | Model discovery, metadata, downloads (incl. gated models), license metadata source | Free | API rate limits (anonymous ~hourly cap; authed via operator's token raises it). HF can change policies, deprecate models, restrict gating without notice. | No clean alternative — HF is the de facto repository. Mitigation is caching downloaded artifacts on the vault tier so they survive HF outages. |
| **GitHub** | Source hosting, issue tracking | Free (public repo) | GitHub TOS; Microsoft-owned. | Mirror to a self-hosted Gitea on the homelab; the workflow is portable. |
| **GitHub Actions** | CI for lint, test, build, image push | Free tier (~2000 min/month for public repos) | Same. | Self-hosted runners on the homelab if quotas become tight; or Gitea Actions. |
| **GitHub Container Registry (GHCR)** | Distribution of `krelix-control` and `krelix-agent` images | Free for public images | Same. | Self-host a registry (e.g., Harbor) on the homelab; or push to Docker Hub. |
| **Docker Hub** | Base images (`python:3.12-slim`, `postgres:18`, `redis:7-alpine`, `nvidia/cuda`) | Free for pulls (anonymous rate-limited) | Anonymous pull rate limits can bite during CI. | Push needed base images to GHCR or a self-hosted registry; pin digests in Dockerfiles. |
| **PyPI** | Python package installs at build time | Free | Standard. | Self-hosted PyPI mirror (`devpi`) if availability becomes a problem. |
| **npm registry** | JavaScript package installs at build time | Free | Standard. | Self-hosted (`verdaccio`) if needed. |
| **NVIDIA Container Toolkit / drivers / CUDA** | GPU access for engine containers (container mode) and engines (bare-metal mode) | Free (proprietary) | NVIDIA EULA — generally allows redistribution of the toolkit but not the driver bits. | None practical — NVIDIA is the only path for this hardware. |

## Key Library Dependencies (load-bearing)

These are the dependencies most likely to cause real pain if they break, get abandoned, or change incompatibly. Standard framework pieces (`FastAPI`, `pydantic`, `React`, etc.) are listed in [`stack.md`](stack.md) and not repeated here.

| Library | Purpose | License | Risk profile |
|---------|---------|---------|--------------|
| **`vllm`** | The primary inference engine, exposed via its OpenAI-compatible server. Loaded as a container image (container mode) or as a Python module subprocess (bare-metal). | Apache 2.0 | **High change velocity** — vLLM moves fast; minor versions occasionally break CLI args and behavior. Mitigation: pin engine versions per-deployment (record `engine_version`), test new vLLM versions in a staging slot before global upgrade, surface vLLM version in the UI. |
| **`huggingface_hub`** | All HF API interaction, downloads, cache management, revision pinning, gated-model handling. | Apache 2.0 | Maintained by HF; API can shift but they version cleanly. Risk: HF could change the auth model or rate-limits. Mitigation: pin to a working minor version; track HF API changelogs. |
| **`pynvml`** | Direct NVML bindings for GPU inventory and live state on the host agent. | BSD-3 | Maintained by NVIDIA; reasonably stable. Bound to NVIDIA only — no AMD/Apple Silicon path here. Mitigation: future engine adapters can introduce ROCm/MPS bindings without changing Krelix's data model. |
| **`docker` (docker-py)** | Docker API client used by the agent in container mode. | Apache 2.0 | Mature, well-maintained. Low risk. |
| **`arq`** | Async job queue (Redis-backed, asyncio-native). | MIT | **In maintenance-only mode since early 2025** (per upstream `python-arq/arq`). Bug fixes happen; no new features. For Krelix's job-queue needs (long-running deployments, downloads) arq's stable surface is more than enough. Mitigation: if arq becomes a blocker, swap to **`dramatiq`** (actively developed, also Redis-backed, async support) or **`procrastinate`** (Postgres-backed, removes Redis from the job-queue path) — both are tractable mechanical migrations because arq's surface is small. |
| **`asyncpg`** | Async Postgres driver. | Apache 2.0 | Mature, low risk. |
| **`SQLAlchemy 2.x` + `Alembic`** | ORM + migrations. | MIT | Mature, large community. Low risk. |
| **`echarts` + `echarts-for-react`** | Realtime charts and gauges, esp. for v2 monitoring at 250–500 ms refresh. | Apache 2.0 | Apache-licensed under Apache Foundation governance; very low abandonment risk. Performance at sub-second refresh has been validated externally. |
| **`structlog`** | Structured logging with redaction. | Apache 2.0 / MIT | Mature, low risk. |
| **`pwdlib[argon2]`** | Password hashing. | MIT | Replaces `passlib`, which had its last release in 2020 and does not work on Python 3.13+. `pwdlib` is actively maintained (used by FastAPI Users among others), supports Argon2id + bcrypt with `verify_and_update` for transparent algorithm rotation. Low risk for v1. |

**License audit summary:** All load-bearing libraries are MIT / BSD / Apache 2.0. No AGPL, GPL, or commercial-prohibiting licenses. Reviewed against the operator's commercial-future goal — safe.

## Risks and Mitigations

### Engineering risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Auto-iteration logic doesn't converge for novel models** — Krelix retries N times and still fails on a model the operator could have hand-tuned. | High (especially early) | Medium | The 30-min target is per the canonical MVD demo, not "every model." Iteration logic ships with a known failure-mode catalog (OOM at load, OOM first inference, max-model-len, KV cache, quantization-incompatible flag) and a retry budget. When the loop exhausts, the operator sees the final config + logs (US-M-08) and can manually try US-C-02's config override. The failure-mode catalog grows over time as real failures are encountered — explicit open question in `tech-plan.md`. |
| **Fit-prediction accuracy falls below 90%** on the hand-curated 20-combo test set. | Medium | Medium-high (it's a success criterion) | Prediction logic is centralized in a single module; the prediction is recorded on every `deployment` row with its basis. After v1 has run for a few weeks, query `deployment` to see real-world accuracy and iterate. Don't ship without running the 20-combo test set first. |
| **Time-to-endpoint exceeds 30 min on the canonical demo.** | Medium | High (success criterion #1) | Bottleneck is almost certainly download speed for a multi-GB model. Mitigations: parallel-shard downloads where HF supports it, prefer fast-mirror HF endpoints, surface progress to UI so the operator can see the bottleneck. If MVD demo takes 35 min in practice because the model takes 31 min just to download on the operator's link, that's a known caveat to call out — not a code defect. |
| **vLLM API/CLI change breaks Krelix between releases.** | Medium | Medium | Pin engine versions per-deployment; quarantine engine upgrades; test in dev before rolling. vLLM version is part of the deployment record so regression source is observable. |
| **WebSocket fan-out scaling under v2 metrics push** (250–500 ms × N endpoints × M GPUs). | Medium (when v2 D phase lands) | Medium | v1 architecture uses Redis pub/sub for fan-out which scales fine in a single-process control plane. If v2 needs more, switch to a dedicated message bus — but defer until measured. |
| **Multi-GPU deployments (NVLinked A5000s) interact badly with vLLM tensor parallelism config.** | Medium | Medium | Multi-GPU support is implicitly required for ripper-proxmox to be fully usable. Add a manual override (US-C-02) so the operator can set `--tensor-parallel-size 2` explicitly during early development. Auto-detection of multi-GPU intent is deferred. |
| **MIG instance lifecycle confuses Krelix when the operator changes profiles externally.** | Medium | Medium | Agent does a full GPU inventory refresh on every connection / heartbeat — so external MIG changes get picked up at the next heartbeat. Document for the operator: "After running `nvidia-smi mig ...`, restart the agent or wait for the next heartbeat (~30 s) to see the new layout." |
| **Two-tier copy semantics during a crash mid-copy** leaves inconsistent state (hot copy partial, vault copy partial). | Low | Medium | Use atomic rename pattern: download/copy to `<path>.partial`, then `os.rename` to final path. Re-attempt on agent restart by detecting `.partial` files and resuming or restarting the copy. |

### Operational risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **HuggingFace gated-model approvals aren't in place** when the operator tries to download. | Medium (especially early) | Low (clear error path) | Agent surfaces the 401/403 from HF cleanly; UI prompts operator to approve on huggingface.co. Not a code defect — a user education item documented in the README. |
| **NFS-mounted vault becomes unreachable mid-operation.** | Medium (if NFS is used) | Medium | Agent treats vault unreachable as a non-fatal error — falls back to hot-tier-only operation. Eviction is paused if the vault is the destination of recent copies (don't evict from hot if the copy to vault is incomplete). |
| **GPU passthrough on Proxmox breaks after a host update** and the agent loses GPU access. | Low | High | This is host-OS territory, outside Krelix's scope. Agent reports the issue as `agent_status=offline` and logs the underlying NVML error. Operator's runbook says "Krelix can't see your GPUs" → check Proxmox passthrough → check NVIDIA drivers. |
| **`KRELIX_SECRET_KEY` is lost** (operator wipes the env without backup). | Low | Medium | HF token must be re-entered; sessions invalidated; nothing else is lost. Documented prominently in install runbook and in the rotation section of `auth-and-security.md`. |
| **Postgres data corruption / volume loss without backup.** | Low | High (state is gone) | Backup runbook in `deployment.md`; recovery means re-registering endpoints (re-issuing agent tokens). Model artifacts on disk are independent and re-discoverable on next agent connect. |
| **Disk fills on the control-plane VM** due to image accumulation. | Low | Medium | Document `docker system prune` and image pruning in the runbook. Krelix itself uses negligible disk on the control plane. |
| **NVIDIA driver / CUDA version mismatch between host and container** breaks engine launches. | Medium | High | The NVIDIA Container Toolkit handles this, but only when the host driver supports the CUDA version baked into the engine container image. Agent surfaces the underlying error from NVML clearly. Operator's runbook: "If new vLLM images fail with CUDA version errors, update the host driver or pin to a compatible vLLM image." |
| **Bare-metal agent's pre-installed vLLM venv breaks after a system Python upgrade** (e.g., Debian unattended-upgrades). | Medium | Medium | Recommend the operator pin Python via uv-managed venv (`/opt/krelix/engines/vllm`) using a specific Python version, isolated from system upgrades. Document this in the bare-metal install runbook. |

### Process risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Scope creep during agent-driven build** — agents add features not in the user stories, or over-engineer "future-proofing" beyond v1 scope. | **High** | High | This is the single biggest risk. The work-breakdown phase (skill #4) is where scope-creep is fought tactically: each ticket has acceptance criteria + explicit out-of-scope notes referencing [`scope.md`](scope.md) and [`../02-vision/scope.md`](../02-vision/scope.md). Every ticket should answer "is this in the Must list, the Should list, or Won't Have?" If a ticket can't trace to a Must or Should, it doesn't ship in v1. |
| **Agents under-implement the auto-iteration catalog** — they implement the happy path but skip the recovery cases. | High | Medium | Make the failure-mode catalog an explicit ticket with concrete test cases (each failure mode + expected recovery action), separate from the "deploy a model" ticket. Test cases live next to the code. |
| **Agents drift the engine abstraction toward "vLLM-only forever"** — making it hard to add Ollama/llama.cpp later in v2. | Medium | Medium | Architecture explicitly names an engine-runtime abstraction even though only vLLM is implemented. Work tickets should require an `EngineAdapter` protocol + a `VLLMAdapter` concrete class — not a function that hardcodes vLLM args. |
| **Agents over-build security infrastructure** (e.g., adding RBAC, JWT auth, OPA, etc. because the PDF mentioned them). | Medium | Medium | `auth-and-security.md` is explicit about the v1 minimum-viable posture and tags the heavier stack as "commercial product, not v1." Work tickets must reference these constraints. |
| **Agents skip the deferred-decisions list** in `architecture.md` and over-design components that explicitly have latitude. | Medium | Low | Tickets must respect the "Decisions Deferred to Implementation" list — i.e., not lock those decisions prematurely. |
| **Operator changes scope mid-build** in response to agent output. | Medium | Medium | Vision artifacts in `docs/02-vision/` are the source of truth. Mid-build scope changes either go back through `product-discovery-interviewer` → `product-vision-synthesizer` properly (preferred), or are explicitly captured as v1.x additions, not "while we're in here" scope expansion. |

### Strategic risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Broader-adoption assumption proves wrong** — no one else wants this once v1 ships. | Medium | Medium (the user still benefits) | v1 is built first to scratch the operator's own itch, with broader adoption opportunistic. If broader adoption never materializes, v1 still delivered the operator's stated goal — unblocking ~20 downstream AI use cases. |
| **A competitor ships a near-equivalent product** before v1 launches (e.g., KubeAI adds Krelix-like HF intake, or LM Studio extends to remote endpoints). | Low-Medium | Medium | Differentiator is the **full-lifecycle + multi-endpoint + agent-roadmap** combination, not any single feature. Even if a competitor takes a slice, v3's agentic orchestration is the moat. |
| **vLLM-only commitment limits adoption** — operators who already standardized on Ollama see Krelix as not-for-them and don't try it. | Medium | Medium (it's an OSS tool — adoption can recover with the v2 Ollama adapter) | README explicitly states the v1 engine commitment and the v2 roadmap. Ollama adapter is parked first in [`../01-discovery/parking-lot.md`](../01-discovery/parking-lot.md) deliberately so v1.x lands it fast. |
| **License/IP issue on a downloaded model causes legal headache** for the operator. | Low | Medium | Krelix surfaces declared licenses (US-S-02), warn-and-proceed posture documented. Operator is responsible for license compliance — boilerplate in the README. The commercial product is where this becomes a real enforcement layer. |
