# Open Questions — Krelix

Unresolved items raised during discovery that the planning phase will need to address. Each is specific enough that someone could answer it.

## Scope / validation

- Broader-adoption assumption is unvalidated. v1 is built to scratch the user's own itch; plan for a feedback loop with other multi-GPU homelab operators once something demonstrable exists. **What's the minimum demo / public artifact to start gathering external feedback?**
- vLLM-only is the v1 engine commitment. The PDF's recommended "deep on two paths" (vLLM + Ollama) is rejected for v1 in favor of going deeper on vLLM first. **Confirm this is the right call once the vLLM adapter is implemented and we see how much engine-abstraction surface area was actually needed.**

## Infrastructure / integration

- **Docker host integration architecture.** Krelix must work in the existing Docker + Portainer setup. Does Krelix call the Docker API on each GPU host directly, sit alongside Portainer as an independent peer, or integrate through Portainer's API? Each has trade-offs for ops, security, and user-perception of "what's managing what."
- **GPU resource introspection.** For accurate fit prediction on remote endpoints, Krelix needs to know per-endpoint VRAM availability in close-to-realtime. Does it poll periodically, subscribe to a host-side agent, or query on-demand at deploy time?
- **Cloud GPU endpoint integration scoping (post-v1).** Cloud is parked out of v1. When it returns, which provider/pattern categories must Krelix support? Categories the user already named: (a) "just a VM with GPU passthrough" — looks like a local endpoint, may need zero special integration; (b) provider-native managed/serverless GPU services (RunPod, Modal, Lambda, vast.ai) — likely require per-provider integration. v1.x or v2 should explicitly scope this.

## Security / posture

- **v1 auth/security posture.** The PDF recommends Keycloak + OPA + Vault + SPIFFE — that's enterprise-grade and overkill for a single-operator v1 OSS tool. What's the minimum viable security posture for v1 (e.g., single local admin user, HF token storage, scoped API tokens for the agent surface), while leaving room for the heavier stack to land in the eventual commercial product?
- **Sandboxing for risky operations.** Conversion scripts, `trust_remote_code` cases, and arbitrary model artifacts are real risks even in a single-operator setup. What's the minimum sandboxing approach for v1 — separate containers? gVisor? Just "don't auto-execute conversion scripts on the control plane host"?

## Provenance / metadata

- **License + gating capture at intake.** Need a clear policy: capture declared license metadata at download time and surface it in the UI. Block deployment when license metadata is missing or unresolved? Or warn-and-proceed?
- **Immutable revision pinning.** Per the PDF, every download/deployment/benchmark should pin to a resolved HF commit revision rather than a mutable branch reference. How is this surfaced in the UI — is it transparent to the user, or does the user explicitly pick a revision?
