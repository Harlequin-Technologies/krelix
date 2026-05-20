"""Structlog configuration for the Krelix control plane.

JSON output to stdout for everything — including stdlib loggers used by
uvicorn, asyncio, etc. — and a redaction processor that strips known secret
fields from any emitted event. ``configure_logging`` is idempotent.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

# Field names whose values must never appear in logs. Matched case-insensitively.
_REDACTED_KEYS: frozenset[str] = frozenset(
    {
        "authorization",
        "cookie",
        "hf_token",
        "password",
        "password_hash",
        "secret_key",
        "set-cookie",
        "token",
    }
)

_REDACTED_PLACEHOLDER = "<redacted>"

_configured = False


def _redact_value(value: Any) -> Any:
    """Recursively redact secret-shaped keys inside nested dicts and sequences."""
    if isinstance(value, dict):
        return {
            k: (_REDACTED_PLACEHOLDER if k.lower() in _REDACTED_KEYS else _redact_value(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    return value


def redact_secrets(_logger: WrappedLogger, _method_name: str, event_dict: EventDict) -> EventDict:
    """Structlog processor that replaces values for known secret keys with a placeholder."""
    for key in list(event_dict.keys()):
        if key.lower() in _REDACTED_KEYS:
            event_dict[key] = _REDACTED_PLACEHOLDER
        else:
            event_dict[key] = _redact_value(event_dict[key])
    return event_dict


def configure_logging() -> None:
    """Configure structlog + stdlib logging for JSON output and secret redaction.

    All log records from stdlib loggers (uvicorn, asyncio, etc.) are routed
    through structlog's ``ProcessorFormatter`` so the container emits a single
    consistent JSON-per-line stream.

    Idempotent: subsequent calls short-circuit so importing ``krelix.main``
    from multiple entrypoints does not stack processors.
    """
    global _configured
    if _configured:
        return

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
        redact_secrets,
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    # Replace any pre-existing handlers so uvicorn's default handlers do not
    # double-emit a non-JSON line alongside ours.
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Uvicorn installs its own handlers on these named loggers; we want them to
    # bubble up to root so the JSON formatter wins.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers = []
        uv_logger.propagate = True

    _configured = True
