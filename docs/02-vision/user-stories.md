# User Stories — Krelix

Stories are written as: **As a [persona], I want to [action] so that [outcome].**
Each story has acceptance criteria — concrete, observable conditions that prove the story is complete.

Prioritization uses MoSCoW:

- **Must:** Required for v1. If this is missing, v1 fails.
- **Should:** Important but v1 can ship without it.
- **Could:** Nice to have if time permits.
- **Won't (this release):** Explicitly out of scope for v1.

The single persona is the **Multi-GPU AI Enthusiast / Homelab Operator** (see [personas.md](personas.md)). All stories below are from that persona's perspective. The persona is abbreviated below as "the operator."

---

## Must Have

### US-M-01: Register a local GPU endpoint

**As** the operator
**I want to** register one of my existing Docker hosts (with attached GPU resources) as an endpoint that Krelix can deploy models to
**So that** Krelix can place inference workloads on that endpoint without me having to ssh into the host afterward

**Acceptance criteria:**

- The operator can register an endpoint by providing its connection information through the Krelix UI (the specific mechanism — agent install, Docker API access, etc. — is an architectural decision for the planning phase).
- Krelix records and displays the endpoint's available GPU inventory (model, VRAM size, count) and host resources (CPU cores, RAM).
- After registration, the operator can deploy, stop, and observe models on the endpoint without any further terminal session on the GPU host.
- Multiple endpoints can be registered; the architecture supports 1..N endpoints from day 1, with v1 targeting up to 5.

---

### US-M-02: Configure HuggingFace credentials

**As** the operator
**I want to** store a HuggingFace access token in Krelix
**So that** I can discover and download gated or private models without re-authenticating per action

**Acceptance criteria:**

- The operator can add, update, and remove a HuggingFace token through the Krelix UI.
- The token is stored securely (never logged or displayed back in plaintext after entry).
- Discovery and download operations use the stored token automatically; if a download fails due to missing access (e.g., gated model the user hasn't accepted), the failure surfaces a clear, actionable error.

---

### US-M-03: Browse and search HuggingFace for models

**As** the operator
**I want to** search and browse HuggingFace models from inside the Krelix UI
**So that** I don't have to context-switch to a web browser, copy-paste model IDs, or remember which variant I'm trying

**Acceptance criteria:**

- The operator can search HuggingFace by model name, organization, task, and at least format/quantization filters from the Krelix UI.
- Search results display key metadata for each model: model ID, declared license, size on disk, format (safetensors / GGUF / pt), and quantization (if any).
- The operator can drill into a model's details (file manifest, README content or summary, declared license, gating requirements).

---

### US-M-04: View fit prediction for a model against a registered endpoint

**As** the operator
**I want to** see whether a chosen model will fit comfortably, require CPU offload, or won't fit on any specific registered GPU endpoint
**So that** I don't waste time downloading and attempting to deploy a model that has no chance of running on my hardware

**Acceptance criteria:**

- For any model surfaced in discovery, the operator can request a fit prediction against any registered endpoint.
- The prediction returns one of three clearly-labeled outcomes: **fits comfortably**, **needs CPU offload**, or **won't fit**.
- The prediction takes into account: model size, declared quantization/format, the endpoint's GPU VRAM availability, and host CPU/RAM.
- Prediction accuracy must reach ≥ 90% across a hand-curated set of ~20 model × endpoint combinations the operator personally verifies post-implementation.

---

### US-M-05: Deploy a model to an endpoint via vLLM, with automated config iteration on failure

**As** the operator
**I want to** click "deploy" on a chosen model and target endpoint, and have Krelix download the model, launch it with vLLM, and iterate on configuration if startup fails
**So that** I can go from "I want to try this model" to a working endpoint without making docker-compose files, monitoring logs by hand, copy-pasting errors into ChatGPT, and rerunning manually

**Acceptance criteria:**

- The operator initiates deployment from the Krelix UI by selecting a model and a target endpoint.
- Krelix downloads the model artifact to the endpoint (or to shared storage Krelix manages), then launches a vLLM container on the endpoint with an initial configuration chosen by Krelix.
- If startup fails due to a known recoverable failure mode (e.g., OOM, max-model-len too high for available KV cache, quantization-incompatible flag), Krelix automatically adjusts configuration and retries within a bounded number of attempts.
- If startup ultimately succeeds, the deployment is marked **running**; if it ultimately fails after exhausting retries, the deployment is marked **failed** with the final error visible to the operator.
- The operator does not need to ssh into the GPU host during the deployment flow.
- For the canonical MVD demo: deploying `Qwen2.5-14B-Instruct-AWQ` to the RTX A4000 via vLLM completes in **≤ 30 minutes** end-to-end, including download.

---

### US-M-06: View and copy the inference URL for a running deployment

**As** the operator
**I want to** see and copy the OpenAI-compatible inference URL for any running deployment
**So that** I can point downstream tools (Open WebUI, custom apps, agent frameworks, `curl` smoke tests) at it without reconstructing the URL by hand

**Acceptance criteria:**

- Every running deployment exposes an OpenAI-compatible URL visible in the Krelix UI.
- The URL is one-click copyable.
- A `curl` smoke test against the URL with a standard chat-completions payload returns a valid response.

---

### US-M-07: View deployment status

**As** the operator
**I want to** see, for every deployment, its current status (pending / downloading / starting / running / failed / stopped)
**So that** I know what's happening and whether something needs my attention

**Acceptance criteria:**

- The Krelix UI lists all known deployments with their current status and the endpoint they're on.
- Status transitions are visible in close-to-realtime (no manual refresh required, or refresh is one click).
- Each deployment shows enough metadata to identify it: model name, model revision, endpoint, engine, started timestamp.

---

### US-M-08: View vLLM container logs for a deployment from the Krelix UI

**As** the operator
**I want to** read the vLLM logs of any deployment (in particular, a failed one) directly from the Krelix UI
**So that** when Krelix's auto-iteration ultimately fails, I can diagnose what happened without falling back to ssh + `docker logs`

**Acceptance criteria:**

- The operator can open a log view for any deployment from the Krelix UI.
- The log view shows recent stdout/stderr from the vLLM container.
- The log view is available for **running**, **failed**, and (at least briefly) **stopped** deployments — not just successful ones.
- Live tailing of logs while a deployment is in `starting` state is supported.

---

### US-M-09: Eject / teardown a deployment

**As** the operator
**I want to** stop and remove a deployment from the UI
**So that** I can free up GPU resources to try a different model on the same endpoint

**Acceptance criteria:**

- The operator can stop a running deployment from the Krelix UI.
- After stop, the deployment's vLLM container is removed from the endpoint and the GPU resources it was using are released.
- The operator can confirm via fit prediction (US-M-04) that the released VRAM is again available for a new deployment.

---

## Should Have

### US-S-01: Pin model deployments to immutable HuggingFace revisions

**As** the operator
**I want to** deploy a model pinned to a specific resolved HuggingFace commit/revision rather than the moving `main` reference
**So that** "this exact model was running" is later answerable, and future-me (or future-Krelix C/D phases) can compare runs without ambiguity

**Acceptance criteria:**

- Every download and deployment records the resolved HF revision (commit hash or snapshot reference), not just the model reference like `org/model:main`.
- The resolved revision is visible in the deployment metadata in the UI.
- If the operator deploys the same model reference again later and `main` has moved, this is detectable (the resolved revision differs from a prior deployment of the same reference).

---

### US-S-02: Surface model license metadata at discovery and deployment time

**As** the operator
**I want to** see the declared license of a model both during HuggingFace discovery and at deployment time
**So that** I'm aware of any license obligations before committing GPU resources to it, and so the data is captured for future commercial-product license enforcement

**Acceptance criteria:**

- The license declared in the model card metadata is shown in search results (US-M-03).
- The license is shown again on the deployment confirmation screen.
- Models with unresolved or missing license metadata display a clear warning indicator at both points; deployment is still permitted (warn-and-proceed in v1).

---

### US-S-03: Retain a basic record of past deployment attempts (not full benchmarks)

**As** the operator
**I want to** see a basic history of past deployments — what was deployed where, when, whether it succeeded, and the final config Krelix used — even after a deployment is ejected
**So that** if a config worked once and was lost during teardown, I have at least a paper trail to manually replicate (full C-phase "redeploy-this-known-good-config" is v2)

**Acceptance criteria:**

- After a deployment is stopped/ejected, its record (model, revision, endpoint, engine, final config, success/failure status, timestamps) persists in Krelix.
- The operator can browse past deployment records from the UI.
- This is *not* the full benchmark/known-good-config registry from phase C; no auto-redeploy, no performance metrics — just the history.

---

## Could Have

### US-C-01: Show estimated download time and progress for in-flight model downloads

**As** the operator
**I want to** see how far along a model download is and a rough ETA
**So that** I know whether to wait or grab coffee, especially for large models on slow links

**Acceptance criteria:**

- During a download, the UI shows current bytes / total bytes (or percent complete).
- A rough estimated time remaining is displayed.

---

### US-C-02: Allow the operator to override the initial vLLM configuration before deploy

**As** the operator
**I want to** optionally view and tweak the initial vLLM launch arguments before clicking deploy
**So that** when I already know a config that works (or want to experiment), I'm not forced to wait through Krelix's auto-iteration

**Acceptance criteria:**

- The operator can choose to view/edit the initial vLLM config from the deploy screen, or accept Krelix's defaults.
- If the operator overrides config, Krelix uses the overridden values as the *initial* attempt; auto-iteration still applies on failure.

---

## Won't Have (this release)

The following are explicitly out of scope for v1. See [scope.md](scope.md), [`../01-discovery/parking-lot.md`](../01-discovery/parking-lot.md), and discovery Section 7 (Non-goals).

### US-W-01: Cloud GPU endpoint support
Parked. v1 is local-only. — *v1.x or v2; needs deliberate provider scoping.*

### US-W-02: Benchmark capture, performance metrics history, and known-good config registry (phase C)
Parked to v2. v1 records basic deployment history (US-S-03) but not benchmark metrics or auto-redeploy of known-good configs.

### US-W-03: Holistic endpoint monitoring / livelook (phase D)
Parked to v2. v1 has deployment status and logs (US-M-07/08) but not the full real-time observability surface.

### US-W-04: Agent / MCP interface and agent-driven model selection (phase E)
Parked to v3. v1 does not expose a programmable agent surface.

### US-W-05: Exhaustive optimal-config sweep across (model × engine × hardware × use-case)
Parked to v2/v3 — the "ultimate end goal" benchmark engine. v1's auto-iteration is bounded recovery from common failure modes, not exhaustive search.

### US-W-06: Engine adapters other than vLLM (Ollama, llama.cpp, SGLang, TensorRT-LLM, NIM)
Parked to v2+. v1 is vLLM only.

### US-W-07: Multi-user / RBAC / tenant isolation / audit logs
Belongs to a separate **licensed commercial product**, not v1 OSS. Single-operator only in v1.

### US-W-08: Proxmox VM management, GPU passthrough configuration, host OS setup
v1 targets pre-existing Docker hosts that the operator has configured. Krelix does not manage the virtualization or host layer.

### US-W-09: Chat / RAG UI
Krelix produces an OpenAI-compatible URL. Pointing a chat UI (Open WebUI, etc.) at it is the operator's responsibility.

### US-W-10: Fine-tuning / training capabilities
Inference-side only.

### US-W-11: Kubernetes-native enterprise inference platform features
Out of scope for v1 and the immediate roadmap; long-term exploration only.
