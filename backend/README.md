# Krelix Control Plane (backend)

FastAPI + SQLAlchemy 2 async + arq worker package for the Krelix control plane. See the top-level repository README for product context.

## Quick start

```bash
cd backend
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

The package exposes two entrypoints (registered in `pyproject.toml`):

- `krelix-api` — FastAPI/uvicorn HTTP+WebSocket process.
- `krelix-worker` — arq worker process.
