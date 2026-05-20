"""Entrypoint dispatcher for the ``krelix-api`` and ``krelix-worker`` scripts.

Both scripts ship in the same container image and are selected by Compose
``command:`` overrides; see ``../03-technical/deployment.md``.
"""

from __future__ import annotations

import os
from typing import cast

import uvicorn
from arq.typing import WorkerSettingsType
from arq.worker import run_worker as _arq_run_worker

from .logging import configure_logging
from .worker import WorkerSettings

_DEFAULT_BIND_HOST = "0.0.0.0"  # noqa: S104  -- container-bound; restrict at the network layer
_DEFAULT_BIND_PORT = 8000


def run_api() -> None:
    configure_logging()
    host = os.environ.get("KRELIX_BIND_HOST", _DEFAULT_BIND_HOST)
    port = int(os.environ.get("KRELIX_BIND_PORT", str(_DEFAULT_BIND_PORT)))
    # log_config=None: don't let uvicorn reset the structlog-routed handlers we just installed.
    uvicorn.run("krelix.main:app", host=host, port=port, log_config=None)


def run_worker() -> None:
    configure_logging()
    # arq's WorkerSettingsBase is a Protocol; our settings class is duck-typed against it.
    _arq_run_worker(cast(WorkerSettingsType, WorkerSettings))
