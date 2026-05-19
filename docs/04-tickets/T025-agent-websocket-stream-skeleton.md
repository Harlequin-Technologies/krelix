# T025 — Agent WebSocket stream skeleton + /agent/v1/config

**Status:** Not started
**Phase:** 4 — Endpoint registration + agent bootstrap protocol
**Estimated session length:** 3 hr
**Depends on:** T009, T024
**Blocks:** Phase 5 (host agent code consumes this); Phase 7+ (deploy commands ride this channel)
**Maps to:** `api-contracts.md` "Agent-Facing Endpoints" — `WS /agent/v1/stream` + `GET /agent/v1/config`; `architecture.md` Component 5 communication model.

---

## Objective

Implement the control-plane side of the persistent agent WebSocket: auth on connect via bearer token, accept and respond to `heartbeat` and `ack` frames, register the connection in a connection-registry singleton so other modules (later: deployment orchestrator) can send commands to a known online agent. Also lands `GET /agent/v1/config` for agents to pull resolved config on demand.

Heartbeat-only at this stage — no command frames yet. Those land in Phase 7.

## Context

The WebSocket is the bidirectional spine of all agent ↔ control-plane communication. Auth happens at the upgrade request via the Bearer token; subsequent frames are implicitly trusted. The control plane maintains a registry of connected agents keyed by endpoint_id so that future deployment orchestration can find "the agent for this endpoint" and send commands.

For v1, the registry is **in-process** (a dict on the FastAPI app state) — single control-plane instance is fine. Scaling to multiple control-plane replicas is a v2 concern requiring a shared registry (e.g., via Redis pub/sub).

## Read for context

- [`../03-technical/api-contracts.md`](../03-technical/api-contracts.md) — "WS /agent/v1/stream" frame types
- [`../03-technical/architecture.md`](../03-technical/architecture.md) — Component 5; "Decisions Deferred to Implementation" (frame encoding = JSON-over-WebSocket with `{type, id?, payload}`)
- [`T024-agent-bearer-auth-registration.md`](T024-agent-bearer-auth-registration.md) — shared auth lookup
- [`T009-settings-db-redis-connections.md`](T009-settings-db-redis-connections.md) — DB session usage

## Files to create

- `backend/src/krelix/api/agent/v1/stream.py` — the WebSocket handler
- `backend/src/krelix/api/agent/v1/config.py` — `GET /agent/v1/config`
- `backend/src/krelix/services/agent_registry.py` — in-process registry of connected agents
- `backend/src/krelix/api/agent/v1/frames.py` — Pydantic frame schemas (envelope + heartbeat + ack)
- `backend/tests/test_agent_stream.py` — integration test using `websockets` client against the running ASGI app

## Files to modify

- `backend/src/krelix/api/agent/v1/router.py` — register `stream.py` and `config.py` routes

## Files to NOT touch

- T024 registration code — finalized
- Operator-facing surface — separate

## Steps

1. **Write `services/agent_registry.py`:**
   ```python
   import asyncio
   from dataclasses import dataclass, field
   from datetime import datetime, timezone
   from uuid import UUID
   from fastapi import WebSocket

   @dataclass
   class AgentConnection:
       endpoint_id: UUID
       socket: WebSocket
       connected_at: datetime
       last_heartbeat_at: datetime
       lock: asyncio.Lock = field(default_factory=asyncio.Lock)

   class AgentRegistry:
       """In-process registry. Single control-plane instance only in v1."""
       def __init__(self) -> None:
           self._by_endpoint: dict[UUID, AgentConnection] = {}
           self._lock = asyncio.Lock()

       async def register(self, conn: AgentConnection) -> AgentConnection | None:
           """Returns the previously-connected agent for this endpoint, if any (caller closes it)."""
           async with self._lock:
               prior = self._by_endpoint.get(conn.endpoint_id)
               self._by_endpoint[conn.endpoint_id] = conn
               return prior

       async def unregister(self, endpoint_id: UUID, *, only_if_socket: WebSocket | None = None) -> None:
           async with self._lock:
               existing = self._by_endpoint.get(endpoint_id)
               if existing is None:
                   return
               if only_if_socket is not None and existing.socket is not only_if_socket:
                   return  # newer connection is in place; don't unregister it
               del self._by_endpoint[endpoint_id]

       def get(self, endpoint_id: UUID) -> AgentConnection | None:
           return self._by_endpoint.get(endpoint_id)

       def all_online(self) -> list[AgentConnection]:
           return list(self._by_endpoint.values())

   _registry = AgentRegistry()

   def get_agent_registry() -> AgentRegistry:
       return _registry
   ```

2. **Write `frames.py`:**
   ```python
   from typing import Any, Literal
   from pydantic import BaseModel

   class Envelope(BaseModel):
       type: str
       id: str | None = None
       payload: dict[str, Any] = {}

   class HeartbeatPayload(BaseModel):
       at: str  # ISO timestamp from the agent
       stats: dict[str, Any] = {}  # free-form; v1 may include hot_tier_free_mb, vault_free_mb

   class AckPayload(BaseModel):
       result: Literal["accepted", "rejected"]
       error: str | None = None
   ```

3. **Write `stream.py`:**
   ```python
   from datetime import datetime, timezone
   import structlog
   from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
   from sqlalchemy.ext.asyncio import AsyncSession
   from ...db import _session_factory
   from ...models.fleet import Endpoint
   from .dependencies import _lookup_principal, _parse_bearer
   from .frames import Envelope, HeartbeatPayload
   from ...services.agent_registry import AgentConnection, get_agent_registry

   router = APIRouter()
   log = structlog.get_logger()

   @router.websocket("/stream")
   async def stream(websocket: WebSocket) -> None:
       # Auth on the upgrade request
       try:
           auth = websocket.headers.get("authorization")
           plaintext = _parse_bearer(auth)
       except Exception:
           await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
           return

       # Look up principal — needs a DB session, opened manually for the WS scope
       assert _session_factory is not None
       async with _session_factory() as db:
           try:
               principal = await _lookup_principal(db, plaintext)
           except Exception:
               await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
               return

           await websocket.accept()
           now = datetime.now(timezone.utc)
           conn = AgentConnection(
               endpoint_id=principal.endpoint.id,
               socket=websocket,
               connected_at=now,
               last_heartbeat_at=now,
           )
           registry = get_agent_registry()
           prior = await registry.register(conn)
           if prior is not None:
               # Newer connection wins. Close the old socket.
               try:
                   await prior.socket.close(code=status.WS_1012_SERVICE_RESTART)
               except Exception:
                   pass

           # Reflect online status to the DB once
           principal.endpoint.agent_status = "online"
           principal.endpoint.last_heartbeat_at = now
           await db.commit()

           log.info("agent_connected", endpoint_id=str(principal.endpoint.id))

           try:
               while True:
                   raw = await websocket.receive_json()
                   env = Envelope.model_validate(raw)
                   if env.type == "heartbeat":
                       hb = HeartbeatPayload.model_validate(env.payload)
                       conn.last_heartbeat_at = datetime.now(timezone.utc)
                       principal.endpoint.last_heartbeat_at = conn.last_heartbeat_at
                       await db.commit()
                       # Respond with an ack
                       await websocket.send_json({
                           "type": "ack",
                           "id": env.id,
                           "payload": {"result": "accepted", "error": None},
                       })
                   else:
                       # Unknown frame type for v1 — log and ignore (or ack=rejected)
                       log.warning("unknown_frame", type=env.type, endpoint_id=str(principal.endpoint.id))
                       await websocket.send_json({
                           "type": "ack",
                           "id": env.id,
                           "payload": {"result": "rejected", "error": f"unknown_frame:{env.type}"},
                       })
           except WebSocketDisconnect:
               log.info("agent_disconnected", endpoint_id=str(principal.endpoint.id))
           except Exception as e:
               log.exception("agent_stream_error", endpoint_id=str(principal.endpoint.id), exc_info=e)
           finally:
               await registry.unregister(principal.endpoint.id, only_if_socket=websocket)
               # Mark endpoint offline ONLY if this socket is still the registered one (already enforced above).
               # Reopen a fresh session for the offline-status write (the WS-scoped session may be dirty).
               async with _session_factory() as db2:
                   ep = await db2.get(Endpoint, principal.endpoint.id)
                   if ep is not None and registry.get(ep.id) is None:
                       ep.agent_status = "offline"
                       await db2.commit()
   ```

4. **Write `config.py`:**
   ```python
   from fastapi import APIRouter, Depends
   from sqlalchemy.ext.asyncio import AsyncSession
   from ...db import get_db
   from ...services.resolved_config import resolve_for_endpoint
   from .dependencies import get_authenticated_agent, AgentPrincipal
   from .schemas import ResolvedConfigForAgent

   router = APIRouter()

   @router.get("/config", response_model=ResolvedConfigForAgent)
   async def get_config(
       principal: AgentPrincipal = Depends(get_authenticated_agent),
       db: AsyncSession = Depends(get_db),
   ) -> ResolvedConfigForAgent:
       resolved = await resolve_for_endpoint(db, principal.endpoint)
       return ResolvedConfigForAgent(
           hot_tier_path=resolved.hot_tier_path,
           vault_mount_path=resolved.vault_mount_path,
           eviction_policy_type=resolved.eviction_policy_type,
           eviction_threshold=resolved.eviction_threshold,
           auto_iteration_retry_budget=resolved.auto_iteration_retry_budget,
       )
   ```

5. **Update `api/agent/v1/router.py`:**
   ```python
   from fastapi import APIRouter
   from .register import router as register_router
   from .stream import router as stream_router
   from .config import router as config_router

   agent_v1 = APIRouter(prefix="/agent/v1")
   agent_v1.include_router(register_router, tags=["agent"])
   agent_v1.include_router(stream_router, tags=["agent"])
   agent_v1.include_router(config_router, tags=["agent"])
   ```

6. **Write `tests/test_agent_stream.py`** — integration tests using a real ASGI client:
   - **Happy path:** create endpoint + token via operator API; connect a `websockets` client with `Authorization: Bearer <token>`; send a heartbeat frame; receive ack; close cleanly. Verify endpoint's `agent_status` flipped to `online` then back to `offline` after disconnect.
   - **Bad auth:** connect with no Authorization header → close with 1008.
   - **Revoked token:** revoke the token via operator API; connect → close with 1008.
   - **Replacement:** open WS1, then open WS2 with same token → WS1 receives a 1012 close; WS2 stays open. Registry shows WS2.
   - **Unknown frame type:** send `{"type": "frobnicate", "id": "abc"}` → receive ack with `result: "rejected"`, agent stays connected.
   - **GET /agent/v1/config:** with valid bearer → 200 with resolved config; revoked token → 401.

## Acceptance Criteria

- [ ] `WS /agent/v1/stream` accepts the bearer token via the Authorization header on upgrade.
- [ ] Successful upgrade transitions the endpoint's `agent_status` to `online` and updates `last_heartbeat_at`.
- [ ] Heartbeat frames update `last_heartbeat_at` and are acknowledged.
- [ ] Unknown frame types are acknowledged with `result: "rejected"` and a clear `error` field; the agent stays connected.
- [ ] Disconnect (clean or error) transitions `agent_status` to `offline`, unless a newer connection has already replaced this one.
- [ ] Newer connections win — opening a second WS with the same token closes the prior socket with code 1012.
- [ ] Bad / revoked tokens cause an immediate 1008 close without acceptance.
- [ ] `AgentRegistry` is a module-level singleton accessed via `get_agent_registry()` — used by Phase 7 tickets to find target sockets for commands.
- [ ] `GET /agent/v1/config` returns the resolved config for the authenticated agent's endpoint.
- [ ] Integration tests cover all the cases above and are green.
- [ ] `uv run mypy` clean.

## Out of Scope (for this ticket)

- Any command-type frame handling (deploy, stop, remove_artifact, etc.) — Phase 7
- Log streaming, deployment status reporting, eviction events — Phase 7+
- Periodic stale-connection sweep (close sockets that haven't heartbeated in N minutes) — could be a small follow-up; for v1, agent restart handles this naturally
- Cross-instance agent registry (Redis-backed) — v2 scale concern
- msgpack encoding — JSON over WS for v1 (per architecture's deferred-decisions)
- Frontend updates to show online/offline status — that lives in T026

## Notes

- The DB session inside the WS handler is a bit awkward — FastAPI's `Depends(get_db)` doesn't work for WebSocket routes the same way as for HTTP. The approach above opens a session manually via `_session_factory()`. Surface a cleaner abstraction if you find one — but don't over-engineer.
- Don't store the WebSocket object in the DB — the registry is in-memory by design.
- When opening a second WS for the same endpoint, the "newer wins" pattern matches typical kubelet-style behavior. It also avoids the operator getting stuck if a previous agent process is hung.
- The replaced-socket close uses code 1012 (Service Restart) per RFC 6455 — semantically right for "this connection is being replaced by a newer one." If your WS lib doesn't expose 1012, use 1000 (Normal Closure) as a fallback.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
