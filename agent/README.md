# Krelix Host Agent

The Krelix host agent is a per-GPU-host daemon. One instance runs on each
registered host (in a container or under systemd) and handles all model I/O,
two-tier storage management, GPU introspection via NVML, and the lifecycle of
the inference engine subprocess. It talks to the control plane over a single
authenticated WebSocket and downloads artifacts from HuggingFace directly.
See the top-level [README](../README.md) for product context.

## Quick start

```sh
cd agent
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv run krelix-agent version   # → 0.0.1
```
