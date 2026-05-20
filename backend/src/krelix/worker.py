"""arq worker settings for the Krelix control plane.

No real jobs are registered yet — this is the shape into which later phases
(deployment orchestration, log fan-out, eviction sweeps) will hook their
functions. A single no-op placeholder is registered because arq refuses to
start a worker with zero functions; it can be removed as soon as the first
real job lands.
"""

from __future__ import annotations

import os
from typing import Any, ClassVar

from arq.connections import RedisSettings

_DEFAULT_REDIS_URL = "redis://localhost:6379/0"


async def _noop(_ctx: dict[str, Any]) -> None:
    """Placeholder job so arq's "at least one function" guard is satisfied.

    Remove once a real job is registered (Phase 4+ deployment orchestration).
    """
    return None


def _redis_settings_from_env() -> RedisSettings:
    return RedisSettings.from_dsn(os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL))


class WorkerSettings:
    """arq ``WorkerSettings`` class. arq inspects class attributes directly."""

    functions: ClassVar[list[Any]] = [_noop]
    redis_settings: ClassVar[RedisSettings] = _redis_settings_from_env()
