# Product Requirements Document — Krelix

**Version:** 1.0 (initial vision)
**Date:** 2026-05-18
**Status:** Draft for technical planning
**Source:** Synthesized from [`docs/01-discovery/`](../01-discovery/) plus clarifying questions during vision synthesis.

---

## 1. Overview

Krelix is a control plane for self-hosted AI model operations in a homelab / multi-GPU environment. It simplifies the discovery, download, and automated deployment of HuggingFace models onto local Docker-host GPU endpoints, using the existing best-of-breed inference engines (vLLM in v1; Ollama, llama.cpp, SGLang, TensorRT-LLM, and NVIDIA NIM in later phases) rather than reinventing them. v1 collapses the multi-hour, manual lifecycle of *"find a model → figure out variant/quantization → pick engine → write compose file → debug startup → iterate config → finally have a working endpoint"* into a single UI flow that gets the operator from intent to a working OpenAI-compatible inference URL in 30 minutes or less.

The long-term vision extends Krelix into a full lifecycle command center: benchmark capture and known-good config registry (v2), holistic real-time endpoint monitoring (v2), and ultimately agent-driven model selection where AI agents call into Krelix to pick, deploy, use, and eject models per workload (v3). v1 is the load-bearing foundation: nothing else in that arc is possible without the discover-fit-deploy spine that v1 establishes.

## 2. Problem Statement

The full lifecycle of finding, evaluating, deploying, monitoring, and switching between self-hosted AI models is entirely manual today, and it gates all downstream productive AI agent work. The lifecycle spans: discover models on HuggingFace → determine which variant/quantization will run on available hardware → pick a compatible inference engine → configure engine args → start and babysit it through startup → debug failures via logs → iterate on config → benchmark → record results → and, when switching models, manually stop one engine and start another. Monitoring is ssh + `nvtop` + log-tailing.

**Concrete example:** Trying to get Gemma 4 running consumed an entire evening — figuring out which variant fit the hardware, which quantization, which inference engine, which command-line args, then iterating through start → fail → read logs → tweak → restart until the engine loaded. Evaluating multiple candidate models against a single use case can consume multiple days; across ~20 expected use cases, this would burn roughly a month of dedicated time *before* productive workflow work could start. The same pain repeats every time a promising new model is released.

**The pain ranked:**
1. **Raw time cost from the manual process** — primary pain (an evening per model, days per use case).
2. **No captured knowledge per configuration iteration** — optimal configs get lost or have to be rediscovered.
3. **No way to redeploy a known-good config on demand** — even when a working config is found.
4. **No agent-driven orchestration** — model swaps for sub-agent tasks are manual stop/start.

v1 addresses (1) directly and lays the foundation for (2), (3), and (4) in later phases.

## 3. Goals

**Primary goal:** Cut the time from "I want to try this HuggingFace model" to "I have a working OpenAI-compatible inference URL on the GPU endpoint I chose" from an evening to ≤ 30 minutes, end-to-end, through a single UI, without the operator opening a terminal session on the GPU host post-onboarding.

**Supporting goals:**

- Make multi-endpoint deployment (1..N local GPU hosts) feel as natural as single-host deployment from day 1.
- Extend the LM Studio fit-prediction UX (will it fit? need offload? not fit?) to **remote** GPU endpoints, not just the local box.
- Establish the architectural foundation (registry, deployment intent, lifecycle ownership) that v2 (benchmarking + monitoring) and v3 (agentic orchestration) will build on, without baking either in prematurely.
- Build license/compliance capture in from the start, so the eventual commercial product is not retrofitting it later.

## 4. Target Users

Single primary persona: the **Multi-GPU AI Enthusiast / Homelab Operator** — a technically capable individual running self-hosted inference across multiple GPU resources in their own environment, typically on a virtualization substrate (Proxmox) with Docker hosts managed via Portainer. See [personas.md](personas.md) for the full description, goals, pain points, technical sophistication, and adoption posture.

**Explicit non-users in v1:** Single-GPU individuals (LM Studio mostly serves them), small companies / teams (the eventual commercial product, not v1 OSS), and enterprise / Kubernetes-native AI platform teams (out of scope long-term).

## 5. Functional Requirements

These map to user stories in [user-stories.md](user-stories.md). They enumerate the capabilities v1 must have, organized by area.

### 5.1 Endpoint management

- Register a Docker-host GPU endpoint with Krelix, including discovery of attached GPU inventory and host resources — *(US-M-01)*
- Operate up to 5 registered endpoints simultaneously without manual terminal access post-registration — *(US-M-01, success criterion #2)*
- Stop and remove a deployment from an endpoint, freeing its GPU resources — *(US-M-09)*

### 5.2 HuggingFace integration

- Store and use a HuggingFace access token for gated/private model access — *(US-M-02)*
- Search and browse HuggingFace from the Krelix UI with model metadata visible (ID, license, size, format, quantization) — *(US-M-03)*
- Pin every deployment to an immutable HuggingFace revision and surface it in the UI — *(US-S-01)*
- Capture and surface declared model licenses at discovery and deployment time; warn-and-proceed on missing license metadata — *(US-S-02)*

### 5.3 Fit prediction

- For any model + registered endpoint, predict one of: **fits comfortably**, **needs CPU offload**, or **won't fit** — *(US-M-04)*
- Factor in: model size, declared quantization/format, endpoint GPU VRAM availability, host CPU/RAM — *(US-M-04)*
- Achieve ≥ 90% (95% ideal) prediction accuracy against a hand-curated set of ~20 model × endpoint combinations — *(US-M-04, success criterion #3)*

### 5.4 Automated deployment

- Initiate a model deployment via the UI by selecting a model and target endpoint — *(US-M-05)*
- Download the model artifact to the endpoint (or shared storage Krelix manages) — *(US-M-05)*
- Launch a vLLM container on the endpoint with an initial Krelix-chosen configuration — *(US-M-05)*
- On startup failure caused by a known recoverable failure mode (e.g., OOM, max-model-len, KV-cache, quantization-incompatible flags), automatically adjust configuration and retry within a bounded retry budget — *(US-M-05)*
- Mark the deployment **running** on eventual success or **failed** on exhausted retries with the final error visible — *(US-M-05)*
- *(Optional, Could)* Allow the operator to override the initial vLLM configuration at deploy time — *(US-C-02)*

### 5.5 Inference endpoint exposure

- Expose a working, copyable OpenAI-compatible inference URL for every running deployment — *(US-M-06)*

### 5.6 Deployment observability

- Show current status of every deployment (pending / downloading / starting / running / failed / stopped) — *(US-M-07)*
- Display deployment metadata: model name, resolved revision, endpoint, engine, started timestamp — *(US-M-07)*
- Show vLLM container logs from the Krelix UI for live, failed, and recently-stopped deployments, including live-tailing during startup — *(US-M-08)*
- Persist a basic record of past deployments (model, revision, endpoint, engine, final config, success/failure, timestamps) — *(US-S-03)*
- *(Optional, Could)* Show download progress / ETA — *(US-C-01)*

## 6. Non-Functional Requirements

Things v1 must be true *of*, not just things it must *do*. Where discovery did not address a dimension, that dimension is explicitly marked `[Not specified in discovery]` for the technical-planning phase to address.

- **Performance / time-to-endpoint:** End-to-end deployment of the canonical MVD demo (`Qwen2.5-14B-Instruct-AWQ` on the RTX A4000 via vLLM) must complete in ≤ 30 minutes wall-clock, including download and any internal auto-iteration. See success criterion #1.
- **Capability accuracy:** Fit prediction must achieve ≥ 90% accuracy on the hand-curated test set. See success criterion #3.
- **Reliability / availability:** *[Not specifically quantified in discovery.]* v1 is a single-operator OSS tool, not a 24/7 service. The implicit bar is "works when the operator uses it" — formal uptime / availability targets are not in scope for v1.
- **Security / privacy:**
  - HuggingFace tokens must be stored securely; never logged or displayed in plaintext after entry — *(US-M-02)*.
  - Operations involving untrusted model code (`trust_remote_code`, conversion scripts, third-party containers) must not execute directly on the control-plane host. Exact sandboxing approach is an open question for the planning phase.
  - Single-operator security model is acceptable in v1 (no multi-user auth / RBAC / audit). Heavier security stack is deferred to the commercial product.
- **Compliance:** Capture declared model licenses at intake and surface them in the UI — *(US-S-02)*. Honor HuggingFace gated-model access requirements via operator-supplied tokens. No regulated-industry compliance work in scope.
- **Accessibility:** *[Not specified in discovery.]* Defer to standard web-app accessibility practices in the planning phase if a web UI is chosen; no explicit a11y requirements set for v1.
- **Usability — zero-terminal post-onboarding:** After endpoint registration, the operator must be able to perform every Must-have user story (US-M-01 through US-M-09) without ssh-ing into the GPU host. See success criterion #4.
- **Reproducibility / provenance:** Every deployment should record the resolved HF revision, engine version, and final config — *(US-S-01, US-S-03)*. This is the seed of the C-phase benchmark lab and should not be skipped in v1.
- **Scalability:** v1 is bounded — up to 5 simultaneous local endpoints — by design. Higher scale (cluster-grade, multi-node Kubernetes, multi-tenant) is out of scope. Architecture should not preclude future scaling but should not prematurely build for it.

## 7. Constraints

From [`docs/01-discovery/interview-notes.md`](../01-discovery/interview-notes.md) Section 6:

- **Time:** ASAP. Several downstream projects are blocked waiting for v1. No fixed external deadline; urgency is real and self-imposed.
- **Money:** **$100 total budget.** Effectively rules out paid SaaS/managed services. v1 must be OSS / self-hostable.
- **Operator's available hours:** ~40 hours/week — full-time effort.
- **Technical environment:**
  - 3-node Proxmox 9.1.11 cluster (`dell-proxmox`, `epyc-proxmox`, `ripper-proxmox`) hosting Docker host VMs managed by Portainer.
  - GPUs in fleet: 2× RTX Pro 6000 Blackwell Max-Q 96 GB, 1× RTX A4000 16 GB, 1× RTX A2000 6 GB (on `epyc-proxmox`); 2× RTX A5000 24 GB NVLinked (on `ripper-proxmox`); none on `dell-proxmox`.
  - **Hard requirement:** Krelix must work in this existing Docker + Portainer environment. v1 targets pre-existing Docker hosts; it does NOT manage Proxmox VMs or GPU passthrough.
  - Otherwise, stack technology choices (language, database, control-plane framework, UI framework, etc.) are open and will be decided by the technical-architect-planner skill.
- **Legal / compliance:** Build license/compliance handling in from the start: HuggingFace gated-model access via per-operator tokens, declared license capture at intake, sandboxed handling of `trust_remote_code` and conversion scripts.

## 8. Out of Scope

Full enumeration in [scope.md](scope.md). At a glance: phase C/D/E features (benchmark lab, holistic monitoring, agent orchestration), cloud GPU endpoints, engine adapters other than vLLM, multi-user / RBAC, Proxmox VM management, chat / RAG UI, fine-tuning, Kubernetes-enterprise features, exhaustive optimal-config sweep.

## 9. Success Criteria

Full table in [success-metrics.md](success-metrics.md). At a glance:

1. **Time-to-endpoint ≤ 30 min** on the canonical MVD demo.
2. **Up to 5 endpoints** registered and operable.
3. **Fit-prediction accuracy ≥ 90%** on a curated 20-combo test set.
4. **Zero-terminal post-onboarding** (binary).
5. **vLLM adapter working** end-to-end.
6. **MVD demo reproducible** on demand.
7. **Quietly-public release ready** on GitHub.

Anti-metrics (do NOT optimize for): engine breadth, UI feature count, user/adoption count, hardware breadth beyond own fleet, sub-30-min deploy times, cloud-readiness, new-user onboarding polish.

## 10. Open Questions

Full list in [scope.md](scope.md) under "Open Questions Still to Resolve." Categories: scope/validation (2 questions), infrastructure/integration (4 questions including auto-iteration failure-mode catalog and retry budget), security/posture (2 questions), provenance/metadata (2 questions). These need to be addressed during technical planning or surfaced as decisions during build.

## 11. Assumptions

Explicit assumptions made during synthesis. The technical-planning phase should validate or challenge each.

- The operator's existing Proxmox + Docker + Portainer setup is in working order and the relevant Docker host VMs already have GPU passthrough configured and CUDA / NVIDIA Container Toolkit operational. v1 builds on top of this.
- vLLM is the right *primary* engine to ship in v1. This is to be confirmed empirically once the vLLM adapter is implemented and the engine-abstraction surface area is visible.
- A bounded auto-iteration loop over a finite catalog of common failure modes (OOM, max-model-len, KV cache, quantization-incompatible flags, etc.) is sufficient to make ≥ 30-minute time-to-endpoint feasible for the canonical MVD demo. Catalog and retry budget are an open question.
- A single-operator security model — local admin user, encrypted HF token storage, no multi-user auth — is acceptable for v1 OSS. The heavier enterprise security stack (Keycloak, OPA, Vault, SPIFFE) is deferred to the eventual commercial product.
- "30 minutes" is an acceptable target time-to-endpoint compared with the current evening-per-model baseline. The operator has explicitly endorsed this number.
- Other multi-GPU homelab operators experience pain similar enough to the user's that they would adopt Krelix once available. **This is not yet validated by direct conversation; it is supported by observed behavior** of YouTubers and content creators in the AI/homelab space who use the same tools manually.
- The "quietly public" release posture (GitHub repo + basic README + install steps, no marketing) is sufficient for v1; broader adoption polish (installer, onboarding flows, marketing) is a v1.x+ concern.
- The Proxmox cluster's `dell-proxmox` node (no GPU) is the natural place to run the Krelix control plane itself, separate from the GPU endpoints it manages. This is an architectural hypothesis, not a confirmed decision — the planning phase will validate.
