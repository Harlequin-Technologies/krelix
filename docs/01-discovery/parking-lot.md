# Parking Lot — Krelix

Ideas captured during discovery that are explicitly NOT v1. Each item has a one-line reason for parking and a tentative future phase.

## Feature capabilities

- **C — Benchmark capture and known-good config registry:** Persist benchmark metrics per configuration iteration and let operators redeploy a known-good config on demand. Depends on v1 (A+B) being in place to deploy what gets benchmarked. — *v2*
- **C+ — Exhaustive optimal-config search:** Automated sweep across (model × engine × hardware × use-case) combinations to discover and record optimal configurations. This is the "ultimate end goal" data engine that drives E. — *v2/v3*
- **D — Holistic endpoint monitoring (livelook):** Replace the ssh + nvtop + log-tail workflow with a single observability surface; provides the real-time view that makes C usable. — *v2 (paired with C)*
- **E — Agentic orchestration (dynamic model selection + swap):** Expose the control plane to AI agents so an agent can request the right model for its workload, trigger deployment, use it, and eject. Driven by the decision matrix data produced by C+. Considered "the big deal" of the project strategically, but explicitly NOT v1. — *v3*

## Endpoint topology beyond v1

- **Cloud GPU endpoints:** Dropped from v1 to keep scope bounded and to allow deliberate exploration of which providers / integration patterns to support. Some cloud options (e.g., a rented VM with GPU passthrough) look identical to a local endpoint and may just work; others (provider-native APIs, serverless GPU services like RunPod/Modal/Lambda) require provider-specific integration. — *v1.x or v2 — needs scoping*

## Engine adapters beyond v1

v1 commits to **vLLM only** as the inference engine. Additional engine adapters are deferred:

- **Ollama adapter:** Strong local-model UX, GGUF path. Likely the second engine added after v1 ships. — *v2 (next-adapter priority)*
- **llama.cpp adapter:** GGUF runtime, useful for low-resource and CPU-offload cases. — *v2*
- **SGLang adapter:** Structured outputs, performance routing. — *v2/v3*
- **TensorRT-LLM adapter:** NVIDIA-specific high-performance runtime. — *v2/v3*
- **NVIDIA NIM adapter:** NVIDIA Inference Microservices; higher-level packaged service, NVIDIA-ecosystem dependency. — *v3 (post stabilization)*

## Persona / market expansion

- **Single-GPU individuals as a primary target:** LM Studio/Ollama already mostly serve them; not a design target for v1 but they may adopt opportunistically. — *v2+ (opportunistic, not a design driver)*
- **Small companies / teams (multi-user, RBAC, tenant isolation, audit, role-based approvals):** Intentionally deferred to a separate **licensed commercial product** rather than bolted onto v1 OSS. — *separate commercial track, post-v1*
- **Enterprise / Kubernetes-native platforms team use case:** Not the design target for v1 or the immediate roadmap, but worth revisiting as a long-term exploration once Krelix has matured and the commercial track has been validated. — *long-term exploration, post-commercial*
