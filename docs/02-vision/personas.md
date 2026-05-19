# Personas — Krelix

## Primary Persona: Multi-GPU AI Enthusiast / Homelab Operator

**Role / context:**

A technically capable individual running self-hosted AI inference in their own environment. Typically operates **multiple GPU resources** spread across one or more machines in a homelab setting, often with a virtualization substrate (Proxmox, ESXi, or bare Docker hosts). May occasionally use cloud GPU instances, though cloud is not a primary deployment surface for v1. Comfortable in the Linux terminal, with Docker, and with GPU driver / CUDA setup. Treats their homelab as both a working environment and a tinkering lab — they actively want to try new models as they're released.

The reference instance of this persona is the project author himself: a 3-node Proxmox cluster running Docker host VMs managed by Portainer, with GPU resources spanning consumer (RTX A2000, A4000, A5000) and prosumer (RTX Pro 6000 Blackwell) tiers, totaling ~280 GB of GPU VRAM across nodes.

**Goals:**

- Try new HuggingFace models in their environment **quickly** — minutes, not evenings.
- Stand up working inference endpoints to power downstream AI work (agents, assistants, custom apps, RAG pipelines) without re-doing manual ops per model.
- Use the multi-GPU capacity they already paid for: different models on different endpoints, picked per use case.
- Eventually have AI agents themselves drive model selection and deployment — but they accept this is a future phase.

**Pain points (current state):**

- The full lifecycle of discovering → choosing variant/quantization → choosing engine → configuring → debugging startup → benchmarking is entirely manual.
- One model can eat an evening (Gemma 4 example); evaluating a handful of candidate models per use case can eat days; scaling to ~20 use cases would burn roughly a month before any productive AI agent work begins.
- Working configurations aren't systematically captured, so they get lost or have to be rediscovered.
- Existing tools each solve a slice (LM Studio's local fit prediction, Ollama's local model switching, vLLM's high-throughput inference) but **no single tool unifies the lifecycle across multiple GPU resources**.
- Monitoring inference endpoints today is ssh sessions, `nvtop`, and tailing engine logs — there's no holistic view.

**Technical sophistication:**

**High.** Comfortable with Linux, Docker/containers, GPU drivers, CUDA, Portainer, HuggingFace tooling, multiple inference engines (vLLM, Ollama, llama.cpp). Has personally used Open WebUI, LM Studio, and several runtimes. Does not need hand-holding through technical concepts but explicitly does not want to keep doing the manual ops dance.

**How they'd find / adopt this product:**

For v1: the user *is* the primary adopter (scratching own itch). Posture for v1 ship is "quietly public" — code on GitHub with a basic README and install steps, no marketing — so other operators in this profile may discover it organically through AI/homelab communities (Reddit, Discord, YouTube AI content creators). Broader adoption validation happens after v1 is demonstrable.

## Explicit Non-Users (v1)

These personas are deliberately not designed for in v1:

- **Single-GPU individuals.** LM Studio and Ollama already mostly serve them; Krelix's multi-endpoint and remote-GPU advantages are wasted on a single-box setup. They can use v1 opportunistically, but they're not the design target.
- **Small companies / teams.** They would require multi-user auth, RBAC, tenant isolation, audit logging, and role-based deployment approvals — none of which belong in v1. Company-shaped needs are the eventual target of a separate **licensed commercial product**, not v1 OSS.
- **Enterprise AI platforms teams / Kubernetes-native shops.** Krelix is not competing with KServe / KubeAI / Ray Serve on enterprise terms. Long-term exploration possible post-commercial, but explicitly out of scope for v1 and the immediate roadmap.
