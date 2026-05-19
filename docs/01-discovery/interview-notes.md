# Discovery Interview — Krelix

**Date:** 2026-05-18
**Interviewer:** Claude (product-discovery-interviewer skill)

## 1. Problem

The full lifecycle of finding, evaluating, deploying, monitoring, and switching between self-hosted AI models in a homelab/GPU environment is entirely manual, and it gates all downstream productive AI agent work.

The lifecycle today spans: discover models on HuggingFace → determine which variant/quantization/format will run on available hardware → pick a compatible inference engine → configure engine args → start and babysit it through startup → debug failures via logs → iterate on config → benchmark quality and performance → record results → score and rank → and, when switching models for a different sub-agent task, manually stop the current engine and start a new one. Monitoring is also manual (ssh + nvtop + tailing engine logs for prompt-processing speed, tokens/sec, etc.).

**Concrete example:**

Trying to get Gemma 4 running consumed an entire evening — figuring out which variant in the family would fit the hardware, which quantization, which inference engine supported it, what command-line args were needed, then iterating through start → fail → read logs → tweak config → restart until it loaded. Only after all that could quality and performance benchmarking begin. Evaluating multiple candidate models against a single use case can consume multiple days; doing this across ~20 expected use cases would burn roughly a month of dedicated time *before* any productive workflow work could start. The same pain repeats every time a promising new model is released and needs to be re-evaluated as a potential replacement.

**The pain:**

- **Raw time cost from the manual process** — primary pain; an evening per model, days per use case, a month-plus before productive work can begin.
- **No captured knowledge per configuration iteration** — benchmark metrics and known-good config combinations aren't systematically recorded, so optimal settings can be lost or have to be rediscovered.
- **No way to redeploy a known-good config on demand** — even when a working configuration is found, there's no mechanism to recall and redeploy it cleanly.
- **No agent-driven orchestration** — when an AI agent needs a different model for a sub-task, swapping inference engines is a manual stop/start operation rather than something the agent can request itself. *(Noted as part of the broader pain — scope for v1 vs. later phases will be decided in Section 3.)*

## 2. Current Alternatives

The market has many strong individual components but no single product that unifies discovery → deployment → benchmarking → monitoring → agent-driven orchestration into one control plane (validated by an external landscape scan; see also `_ref/LLM Command Center Market and Architecture Report.pdf` once added). The user has personally used several of the building blocks:

- **Ollama (personally used, as a serving engine):** Good local model-switch UX, but no fleet/control-plane layer — doesn't manage remote/cloud GPU endpoints, no benchmark history, no agent-safe management surface.
- **vLLM (personally used, as a serving engine):** Excellent inference engine (high-throughput, concurrent, OpenAI-compatible). Bare engine — no artifact registry, no benchmark database, no fleet control UI. Deploying and monitoring it across endpoints is all manual.
- **llama.cpp (personally used, as a serving engine):** Same shape as vLLM/Ollama — a runtime, not a control plane.
- **LM Studio (personally used):** Has the *exact* fit-prediction UI the user wants — tells you whether a model will fit comfortably, require CPU offload, or not fit at all. **Critical gap:** it only evaluates resources local to the machine running LM Studio. It cannot evaluate or manage remote GPU resources elsewhere in the environment or in the cloud — which is the actual deployment topology that matters.
- **Open WebUI (personally used, as a chat interface):** Strong human UI for talking to deployed models, but doesn't own the lifecycle — no model discovery/intake, no benchmark history, no deployment orchestration.
- **The "composed stack" alternative (e.g. KubeAI + vLLM/TGI/Ollama + lm-eval + Prometheus + MLflow):** The closest functional competitor today, but it isn't a product — it's a build-it-yourself integration project where the user still owns all the glue, mental model, and operator UX. The integration burden is exactly the pain Krelix is trying to remove.

**User's stance on existing tools:** "I'm not going to reinvent the wheel." vLLM already does concurrent LLM inference well; Ollama already handles local model switching; LM Studio already has a great fit-prediction UI. Krelix should **wrap and orchestrate these tools, not replace them.**

## 3. Proposed Solution

Krelix is a control plane for self-hosted AI model operations. It simplifies the discovery, download, and deployment of models and inference engines to both local and cloud GPU resources, gives a holistic view and cataloging of GPU resources and inference-engine performance, and ultimately allows agentic integration into the control plane so AI agents can automatically select and deploy the right model for their workload. Krelix orchestrates the existing best-of-breed runtimes (vLLM, Ollama, llama.cpp, etc.) rather than replacing them.

**v1 scope (load-bearing wall):**

- **A — Discovery + fit prediction + download:** Browse/search HuggingFace, predict whether a model will fit a chosen GPU endpoint (extending the LM Studio fit-prediction UX to **remote** GPU resources, not just local), and automate the artifact intake.
- **B — Automated deployment:** Take a downloaded model and stand it up on a registered GPU endpoint with the right inference engine and config, producing a working callable inference URL.

A and B must be **fully integrated** in v1 — A alone doesn't relieve the time-vampire pain (the bulk of which is in deploy/configure/debug), so v1 is only useful if a discovered model can be turned into a working endpoint end-to-end.

**Future phases (parked, see [`parking-lot.md`](parking-lot.md)):**

- **v2 — C: Benchmark capture and known-good config registry** (so working configs are never lost).
- **v2 — D: Holistic endpoint monitoring** (replaces the ssh + nvtop + log-tail workflow; provides the livelook surface that makes C usable).
- **v3 — E: Agentic orchestration** — AI agents call into the control plane to select and swap models per workload. *Considered "the big deal" of the project strategically, but explicitly NOT v1.*

**Core value proposition:**

Krelix lets a homelab / self-hosted AI operator go from "I want to try this model from HuggingFace" to "I have a working inference endpoint on the GPU I chose" in minutes instead of an evening — across both local and remote GPU resources.

**What makes it different:**

- vs. **LM Studio:** extends the fit-prediction UX beyond local resources to remote/cloud GPU endpoints — the actual deployment topology that matters in a homelab/multi-machine setup.
- vs. **Ollama / vLLM / llama.cpp:** orchestrates and automates them rather than replacing them — Krelix is the layer above the runtimes.
- vs. **Open WebUI:** owns the model *lifecycle* (intake → deployment), not just the chat UI on top of an already-deployed model.
- vs. **the composed stack (KubeAI + vLLM + lm-eval + Prometheus + MLflow):** provides the integration as a product instead of leaving the operator to build the glue themselves.

## 4. Target User

**Primary persona:**

The **multi-GPU AI enthusiast / homelab operator** — a technically capable individual running self-hosted inference in their own environment, typically with multiple GPU resources, possibly across multiple machines, and with occasional use of cloud GPU instances. They are comfortable in the terminal, can configure Linux/Docker/CUDA, and actively want to experiment with new models for AI agent and assistant workloads. They feel the time-vampire pain acutely because the lifecycle (discover → fit → download → deploy → benchmark → swap) repeats per model and per use case, and they have neither the patience nor the time to keep doing it by hand.

This persona is essentially the user themselves. v1 is built to scratch the user's own itch — and the assumption (not yet validated by conversation, but supported by observed behavior) is that other operators in this profile are doing the same manual dance and would adopt Krelix once it exists.

**Explicitly NOT for:**

- **Single-GPU individuals.** LM Studio and Ollama already mostly serve them; Krelix's multi-endpoint and remote-GPU advantages are wasted on a single-box setup. They can use v1 if they want, but they're not the design target.
- **Small companies / teams.** They would need multi-user auth, RBAC, tenant isolation, audit logging, and role-based approvals — none of which belong in v1. Company-shaped needs are the eventual target of a separate **licensed commercial product**, not v1 OSS.
- **Enterprise AI platforms teams.** Krelix is not a Kubernetes-native enterprise inference platform competing with KServe/KubeAI on those terms — it's a homelab/single-operator control plane.

**Grounding:**

- The primary user is the project author himself, who lives this pain daily.
- Observed (not interview-validated) behavior: AI YouTubers and content creators in the homelab/AI space are still launching inference engines with full CLI argument strings, hand-rolling Docker compose files, running scripts to benchmark, and manually capturing metrics — i.e. the same manual dance the user is on. They use the tools but not orchestrated.
- **Honest validation gap:** the user has not yet interviewed others to confirm they would adopt a control-plane product. v1 will be built to scratch the user's own itch first; broader validation comes after something is usable to show.
- **Strategic note:** the user anticipates that once v1 is known, other individuals in this profile may adopt it relatively quickly. The company / team use case is intentionally deferred to a future **licensed commercial product**.

## 5. Success Criteria for v1

- **Time-to-endpoint ≤ 30 minutes** for trying a new model for the first time in your environment (includes download time plus any configuration iteration needed to find a working combination). Compare to the current baseline of an entire evening. *[Clarified during synthesis: Krelix performs the iteration itself — pick initial config, start container, monitor logs, retry with adjusted config on common failures, return success or final failure. The user does not participate in the iteration loop. Exhaustive optimal-config search across model × engine × hardware combinations is explicitly a later phase, not v1.]*
- **Endpoint scale up to 5 GPU resources, all local.** *[Clarified during synthesis: Cloud GPU endpoint support is dropped from v1 and parked. The user wants to deliberately explore which cloud providers / integration patterns to support — some are essentially "VM with GPU passthrough" (looks like a local endpoint) while others require provider-specific integration. That exploration is part of post-v1 scoping.]*
- **Fit-prediction accuracy ≥ 90%** (95% ideal) when predicting whether a model will fit comfortably, require CPU offload, or not fit on a chosen registered endpoint. *[Clarified during synthesis: testable via a hand-curated set of ~20 model × endpoint combinations the user will personally verify by deploying each and observing actual behavior, then compare to Krelix's prior prediction.]*
- **Zero-terminal post-onboarding.** Once a GPU resource is registered with Krelix, the operator should never need to ssh into it for model ops — only for OS/driver maintenance unrelated to Krelix.
- **Engine coverage: vLLM at minimum** for v1. Additional engines (Ollama, llama.cpp, TensorRT-LLM, NVIDIA NIM, SGLang) are explicitly deferred to later phases (see [`parking-lot.md`](parking-lot.md)).

**Minimum viable definition:**

A single user can register **any local GPU endpoint** with Krelix (architecture handles 1..N endpoints from day 1 — one endpoint is a special case of N), browse HuggingFace for a model from the Krelix UI, see a fit prediction for that endpoint, click "deploy," and have Krelix download the model and launch a vLLM container with appropriate config on the endpoint, producing a working OpenAI-compatible inference URL that responds to a `curl` test — **all without opening a terminal on the GPU host** (beyond initial Krelix-agent install).

**Canonical MVD demo target:**

Deploy **`Qwen2.5-14B-Instruct-AWQ` on an RTX A4000 via vLLM in under 30 minutes**, end-to-end, through the Krelix UI.

**Cloud-endpoint scope for MVD:**

Local-only for both MVD and v1 ship. *[Clarified during synthesis: Cloud endpoint support has been dropped from v1 entirely and parked — see `parking-lot.md`. v1 is local-only.]*

## 6. Constraints

- **Time:** ASAP. Several downstream projects are blocked waiting for Krelix v1 to exist. No fixed external deadline, but urgency is real and self-imposed.
- **Money:** **$100 total budget.** Effectively rules out paid SaaS/managed services; v1 must be OSS / self-hostable. Cloud GPU testing must be done frugally (one-off rentals only, if at all).
- **User's available hours:** ~40 hours/week — effectively full-time effort. Velocity assumptions can be aggressive.
- **Technical environment:**
  - **Substrate:** 3-node Proxmox 9.1.11 cluster:
    - `dell-proxmox.dropthe8.com` — Intel i9-10900, 32 GB RAM, 256 GB NVMe boot. No GPU (likely control-plane / orchestration node).
    - `epyc-proxmox.dropthe8.com` — AMD EPYC 7763, 512 GB RAM, 1 TB NVMe boot + 8 TB NVMe data. **GPUs: 2× RTX Pro 6000 Blackwell Max-Q 96 GB, 1× RTX A4000 16 GB, 1× RTX A2000 6 GB.**
    - `ripper-proxmox.dropthe8.com` — AMD Threadripper PRO 5955WX, 256 GB RAM, 1 TB NVMe boot + 8 TB NVMe data. **GPUs: 2× RTX A5000 24 GB connected via NVLink.**
  - **Container orchestration:** Several Docker host VMs already running on the cluster, managed via **Portainer**.
  - **Hard requirement:** Krelix must work in this existing Docker/Portainer environment first. v1 assumes GPU-accessible Docker hosts pre-exist (Krelix targets them; it does NOT manage Proxmox VM provisioning or GPU passthrough setup in v1).
  - **Open on stack:** Otherwise, technology choices (language, database, control-plane framework, etc.) are open and will be driven by performance, scalability, and fit during the technical-planning phase.
- **Legal / compliance:** Bare minimum is "works for me, local," but the end goal is broader adoption by others, so building license/compliance handling in from the start is acceptable. Specifically in scope from day 1:
  - HuggingFace gated-model access via per-user/per-tenant tokens
  - Capturing declared model licenses in the registry
  - Treating `trust_remote_code` and conversion-script execution as untrusted (sandboxing posture — exact design deferred to planning phase)

## 7. Explicit Non-Goals

1. **Krelix is NOT a new inference engine.** It orchestrates vLLM (and later Ollama, llama.cpp, SGLang, TensorRT-LLM, NIM) — it does not implement model serving itself.
2. **Krelix v1 is NOT a multi-tenant / multi-user platform.** Single operator. No RBAC, no per-user quotas, no audit logs. Multi-user features are the eventual scope of the licensed commercial product, not v1 OSS.
3. **Krelix v1 does NOT manage Proxmox VMs, GPU passthrough, or host OS setup.** Krelix targets pre-existing Docker hosts that the operator has already configured for GPU access.
4. **Krelix v1 is NOT a benchmark lab or experiment tracker.** No automated benchmark suite, no per-iteration metrics capture, no config history, no comparative analytics. (That's C/D in v2.)
5. **Krelix v1 does NOT expose an agent / MCP interface.** No agent-driven model selection, no dynamic swap, no workload-aware routing. (That's E in v3 — the "cherry on top," explicitly disclaimed from v1.)
6. **Krelix v1 is NOT a chat / RAG UI.** It produces an OpenAI-compatible endpoint URL — what the operator points at it (Open WebUI, custom apps, agent frameworks) is the operator's problem.
7. **Krelix v1 is NOT a fine-tuning / training platform.** Inference-side only.
8. **Krelix v1 is NOT a Kubernetes-native enterprise inference platform.** It is a Docker + Portainer homelab control plane in v1.
9. **Krelix v1 does NOT do automatic regression benchmarking, automatic model rotation, or "find the best deployment for this alias" experiments.** Those belong to the C/E phases, not v1.
