# Krelix

**The inference control plane built for AI agents.**

Krelix manages your GPU fleet, model storage, and deployment pipeline — and gives agents an API to dynamically load the right model on the right GPU for the job, then eject it when done.

## What it does

Krelix is a unified control plane for self-hosted LLM inference infrastructure. It sits between your GPU servers and the agents, applications, and workflows that need inference capacity.

**Infrastructure management**
- Real-time monitoring of GPU servers (local or cloud) — CPU, RAM, swap, GPU, VRAM utilization
- Deploy inference engines (vLLM, Ollama, llama.cpp, and more) to GPU servers as Docker containers, Portainer stacks, or bare metal instances
- Track deployed models and inference performance metrics across your fleet

**Model lifecycle**
- Browse, filter, and download models directly from HuggingFace
- Vault tier for centralized model storage; hot tier per GPU server for loaded models
- Local database tracks model metadata, deployment history, and configurations

**Benchmarking**
- Run benchmarks against any model on any GPU server with any inference engine
- Store benchmark results tied to the full configuration (hardware, engine, model, settings)
- Iterate to find optimal configurations for specific use cases

**Agent integration**
- API for AI agents to request model deployments on demand
- Agents can load a model, run a workload, eject it, and request a different model — all programmatically
- Designed for multi-agent systems where sub-agents need different models for different tasks

## Repository Layout

- `backend/` — FastAPI control-plane service (API, ORM, arq workers, auth).
- `frontend/` — React + Vite + TypeScript single-page app served by the control plane.
- `agent/` — Per-host Krelix agent (model I/O, two-tier storage, GPU introspection, inference-engine lifecycle).
- `packaging/` — Dockerfiles, compose files, and `packaging/systemd/` units for bare-metal installs.
- `docs/` — Discovery, vision, technical plan, and per-ticket work breakdown.
- `.claude/` — Planning skills and agent-tooling configuration (not source).

## Local Development

A single `make dev` command brings up a complete local dev environment: Postgres + Redis in containers, and the backend, worker, and frontend running natively for fast iteration.

```bash
cp .env.example .env   # then edit KRELIX_SECRET_KEY
make dev-services      # boot Postgres + Redis
make dev-backend       # in another terminal
make dev-worker        # in another terminal
make dev-frontend      # in another terminal
```

See [`docs/dev-setup.md`](docs/dev-setup.md) for the full walkthrough, prerequisites, and tear-down instructions. Run `make help` to list all available targets.

## Status

Krelix is under active development. Expect breaking changes.

## License

Apache License 2.0. See [LICENSE](LICENSE) for details.

---

Built by [Harlequin Technologies](https://github.com/Harlequin-Technologies).
