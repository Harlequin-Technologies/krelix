# Scope — Krelix

## In Scope (v1)

These map 1:1 to the Must-have and Should-have stories in [user-stories.md](user-stories.md). v1 is not done until everything in this section is true.

### Must (v1 ships when all are working)

- Register and manage 1..N local Docker-host GPU endpoints — *(US-M-01)*
- Store and use HuggingFace credentials for gated/private model access — *(US-M-02)*
- Browse and search HuggingFace from the Krelix UI with key metadata visible — *(US-M-03)*
- Predict whether a chosen model will fit / need offload / not fit on a chosen registered endpoint — *(US-M-04)*
- Deploy a chosen model to a chosen endpoint via vLLM, including download, container launch, and bounded auto-iteration on common config failures — *(US-M-05)*
- Expose a working, copyable OpenAI-compatible inference URL for every running deployment — *(US-M-06)*
- Show current deployment status across all known deployments — *(US-M-07)*
- Show vLLM container logs from the Krelix UI for live, failed, and recently-stopped deployments — *(US-M-08)*
- Stop and remove a deployment, freeing its GPU resources for re-use — *(US-M-09)*

### Should (target for v1, may slip without failing v1)

- Pin every deployment to an immutable HuggingFace revision and surface the resolved revision in the UI — *(US-S-01)*
- Capture and surface declared model licenses at both discovery and deployment time (warn-and-proceed on missing) — *(US-S-02)*
- Persist a basic record of past deployments (model, revision, endpoint, engine, final config, success/failure, timestamps) — *(US-S-03)*

### Could (only if time and complexity permit; not v1-ship-blocking)

- Download progress / ETA in the UI — *(US-C-01)*
- Optional manual override of initial vLLM config at deploy time — *(US-C-02)*

### Engine commitment for v1

- **vLLM only.** No other inference engine adapter (Ollama, llama.cpp, SGLang, TensorRT-LLM, NIM) ships in v1. The architecture should leave room for future adapters without requiring rewrites, but **only vLLM** is implemented in v1.

### Endpoint topology for v1

- **Local Docker-host GPU endpoints only.** Up to 5 endpoints expected. No cloud endpoint support in v1.

### Release posture for v1

- **"Quietly public":** code on GitHub (`Harlequin-Technologies/krelix`), a basic README and install steps, no marketing or launch. v1 is built primarily to scratch the user's own itch; broader adoption is opportunistic.

---

## Out of Scope (v1)

This is the scope-creep firewall. Anything below requires explicit re-scoping to ever enter v1.

### From discovery non-goals (Section 7)

- Krelix is **not** a new inference engine; it orchestrates existing runtimes only.
- Krelix v1 is **not** a multi-tenant / multi-user platform. No RBAC, per-user quotas, audit logs, or role-based deployment approvals.
- Krelix v1 does **not** manage Proxmox VMs, GPU passthrough configuration, or host OS setup. v1 targets pre-existing Docker hosts.
- Krelix v1 is **not** a benchmark lab, experiment tracker, or performance-metrics historian.
- Krelix v1 does **not** expose an agent / MCP interface or programmable management API for AI agents.
- Krelix v1 is **not** a chat / RAG UI.
- Krelix v1 is **not** a fine-tuning / training platform.
- Krelix v1 is **not** a Kubernetes-native enterprise inference platform.
- Krelix v1 does **not** perform automatic regression benchmarking, automatic model rotation, or "find the best deployment for this alias" experiments.

### From the parking lot

Future features and personas, parked with tentative phase:

- **C — Benchmark capture and known-good config registry** — *v2*
- **C+ — Exhaustive optimal-config search** (the "ultimate end goal" data engine that drives E) — *v2/v3*
- **D — Holistic endpoint monitoring / livelook** — *v2 (paired with C)*
- **E — Agentic orchestration** (dynamic model selection + swap, MCP / agent API) — *v3*
- **Ollama engine adapter** — *v2 (next-adapter priority after vLLM)*
- **llama.cpp engine adapter** — *v2*
- **SGLang engine adapter** — *v2/v3*
- **TensorRT-LLM engine adapter** — *v2/v3*
- **NVIDIA NIM engine adapter** — *v3*
- **Cloud GPU endpoint support** — *v1.x or v2; needs deliberate scoping of which providers and integration patterns (VM-with-passthrough vs. provider-native serverless)*
- **Single-GPU individuals as a primary target** — *opportunistic v2+, not a v1 design driver*
- **Small companies / teams (multi-user, RBAC, tenant isolation, audit, role-based approvals)** — *separate licensed commercial product, post-v1*
- **Enterprise / Kubernetes-native use case** — *long-term exploration, post-commercial*

### From "Won't Have" user stories

All `US-W-*` stories in [user-stories.md](user-stories.md) — cloud endpoints, phase C/D/E features, other engines, RBAC, Proxmox management, chat UI, fine-tuning, K8s enterprise features.

---

## Open Questions Still to Resolve

These need answers during technical planning (`technical-architect-planner`) or as v1 is built. They were carried forward from [`../01-discovery/open-questions.md`](../01-discovery/open-questions.md) plus a small number surfaced during synthesis.

### Scope / validation

- **Adoption-feedback loop.** v1 is built to scratch the user's own itch; the broader-adoption assumption is unvalidated. What's the minimum demo or public artifact to start gathering external feedback from other multi-GPU homelab operators post-v1?
- **vLLM-only commitment.** vLLM-only is the v1 engine choice. Confirm this is the right call once the vLLM adapter is implemented and the engine-abstraction surface area is visible — i.e., make sure we haven't accidentally hard-coded vLLM-isms.

### Infrastructure / integration

- **Docker host integration architecture.** Krelix must work with the existing Docker + Portainer setup. Does Krelix call the Docker API on each GPU host directly, sit alongside Portainer as an independent peer, or integrate through Portainer's API? Trade-offs in ops, security, and "what is managing what" perception.
- **GPU resource introspection cadence.** For accurate fit prediction on registered endpoints, Krelix needs per-endpoint VRAM availability in close-to-realtime. Polling? Host-side agent? On-demand query at deploy time?
- **Cloud GPU integration scoping (post-v1).** When cloud returns from the parking lot, which provider/pattern categories must Krelix support? (a) VM with GPU passthrough (looks like a local endpoint, possibly zero special integration); (b) provider-native managed/serverless GPU (RunPod, Modal, Lambda, vast.ai — per-provider integration likely).
- **Auto-iteration scope and bound.** What is the catalog of "common failure modes" Krelix should handle automatically (OOM, max-model-len, KV cache, quantization-incompatible flags, etc.), and what is the maximum bounded retry budget per deployment?

### Security / posture

- **v1 auth/security posture.** The PDF recommends Keycloak + OPA + Vault + SPIFFE — enterprise-grade and overkill for a single-operator v1 OSS tool. What is the minimum viable security posture for v1 (local admin user, HF token storage approach, scoped API tokens for future agent surface), while leaving room for the heavier stack to land in the commercial product?
- **Sandboxing for risky operations.** Conversion scripts, `trust_remote_code` cases, and arbitrary model artifacts remain risks even in a single-operator setup. What is the minimum sandboxing approach for v1 — container isolation only, gVisor, or simply "do not auto-execute conversion scripts on the control-plane host"?

### Provenance / metadata

- **License + gating capture policy.** Policy for v1: capture declared license metadata at download time and surface it in the UI. Block deployment when license metadata is missing or unresolved, or warn-and-proceed? (US-S-02 currently states warn-and-proceed; confirm during planning.)
- **Immutable revision pinning UX.** Per the PDF, every deployment should pin to a resolved HF commit revision rather than a mutable branch reference. How is this surfaced in the UI — transparent to the operator, or does the operator explicitly pick a revision?
