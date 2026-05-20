"""FastAPI application factory for the Krelix control plane.

Exposes a module-level ``app`` so uvicorn can import it as ``krelix.main:app``.
At this stage only liveness (``/healthz``) and readiness (``/readyz``) routes
exist; real DB/Redis readiness wiring lands in T009.
"""

from __future__ import annotations

from fastapi import FastAPI

from .logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Krelix Control Plane", version="0.0.1")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        # TODO(T009): wire real DB + Redis readiness checks
        return {"status": "ready"}

    return app


app = create_app()
