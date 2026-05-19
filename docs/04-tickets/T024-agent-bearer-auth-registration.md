# T024 — Agent bearer-token auth + Agent registration endpoint

**Status:** Not started
**Phase:** 4 — Endpoint registration + agent bootstrap protocol
**Estimated session length:** 2.5 hr
**Depends on:** T010, T023
**Blocks:** T025
**Maps to:** `api-contracts.md` "Agent-Facing Endpoints (`/agent/v1`)" — `POST /agent/v1/register`; `auth-and-security.md` "Authentication / Agent surface"; `data-model.md` `agent_registration_token` lifecycle.

---

## Objective

Implement the shared agent bearer-token auth dependency (used by both HTTP and WebSocket entry points) and the `POST /agent/v1/register` endpoint. On a successful first-time registration, the token is marked `consumed_at`, the endpoint row is updated with reported metadata, and `gpu_resource` rows are upserted from the agent's report. Response includes the resolved config and the WebSocket URL the agent should connect to next.

## Context

This is the agent-side counterpart to T023. The operator-side flow created an endpoint row + token. Now the agent presents that token on `POST /agent/v1/register` and the control plane links the agent's reported reality (GPUs, runtime mode, version) to the endpoint row. After registration, the agent opens a persistent WebSocket (T025) using the same token for ongoing communication.

The endpoint is **CSRF-exempt** (per T015's exempt path list `/agent/`) — agent surface uses bearer-token auth, not session cookies.

## Read for context

- [`../03-technical/api-contracts.md`](../03-technical/api-contracts.md) — "Agent-Facing Endpoints" section in full
- [`../03-technical/auth-and-security.md`](../03-technical/auth-and-security.md) — "Authentication / Agent surface" subsection
- [`../03-technical/data-model.md`](../03-technical/data-model.md) — `agent_registration_token`, `endpoint`, `gpu_resource`
- [`T023-endpoint-crud-api.md`](T023-endpoint-crud-api.md) — token issuance side; `resolve_for_endpoint`

## Files to create

- `backend/src/krelix/api/agent/__init__.py` — empty
- `backend/src/krelix/api/agent/v1/__init__.py` — empty
- `backend/src/krelix/api/agent/v1/router.py` — `agent_v1` APIRouter at prefix `/agent/v1`
- `backend/src/krelix/api/agent/v1/register.py` — `POST /agent/v1/register`
- `backend/src/krelix/api/agent/v1/dependencies.py` — `get_authenticated_agent` (HTTP) + `get_authenticated_agent_ws` (WebSocket)
- `backend/src/krelix/api/agent/v1/schemas.py` — `RegisterRequest`, `GpuReport`, `RegisterResponse`
- `backend/src/krelix/services/gpu_inventory.py` — upsert logic that reconciles reported GPUs with stored rows
- `backend/tests/test_agent_auth.py`
- `backend/tests/test_agent_register_api.py`
- `backend/tests/test_gpu_inventory.py`

## Files to modify

- `backend/src/krelix/main.py` — include the agent router
- `backend/src/krelix/auth/csrf.py` — already has `/agent/` in `EXEMPT_PATHS` (T015). Verify.

## Files to NOT touch

- Operator-facing endpoint routes (T023) — finalized
- Models (T010), migrations (T011)

## Steps

1. **Write `dependencies.py`:**
   ```python
   from fastapi import Depends, Header, HTTPException, WebSocket, status
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select
   from ...db import get_db
   from ...models.auth import AgentRegistrationToken
   from ...models.fleet import Endpoint
   from ...services.agent_tokens import hash_token

   class AgentPrincipal:
       def __init__(self, endpoint: Endpoint, token: AgentRegistrationToken) -> None:
           self.endpoint = endpoint
           self.token = token

   def _parse_bearer(authorization: str | None) -> str:
       if not authorization or not authorization.startswith("Bearer "):
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail={"error": {"code": "missing_bearer_token", "message": "Authorization: Bearer required"}},
           )
       return authorization.removeprefix("Bearer ").strip()

   async def _lookup_principal(db: AsyncSession, plaintext: str) -> AgentPrincipal:
       token_hash = hash_token(plaintext)
       result = await db.execute(
           select(AgentRegistrationToken).where(AgentRegistrationToken.token_hash == token_hash)
       )
       tok = result.scalar_one_or_none()
       if tok is None or tok.revoked_at is not None:
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail={"error": {"code": "invalid_token", "message": "Token invalid or revoked."}},
           )
       ep_result = await db.execute(select(Endpoint).where(Endpoint.registration_token_id == tok.id))
       ep = ep_result.scalar_one_or_none()
       if ep is None or ep.deleted_at is not None:
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail={"error": {"code": "endpoint_gone", "message": "Endpoint is no longer registered."}},
           )
       return AgentPrincipal(endpoint=ep, token=tok)

   async def get_authenticated_agent(
       authorization: str | None = Header(default=None),
       db: AsyncSession = Depends(get_db),
   ) -> AgentPrincipal:
       plaintext = _parse_bearer(authorization)
       return await _lookup_principal(db, plaintext)

   async def get_authenticated_agent_ws(websocket: WebSocket, db: AsyncSession) -> AgentPrincipal:
       """For WebSocket — auth happens in T025; this is the shared lookup callable."""
       auth_header = websocket.headers.get("authorization")
       plaintext = _parse_bearer(auth_header)
       return await _lookup_principal(db, plaintext)
   ```

2. **Write `schemas.py`:**
   ```python
   from typing import Literal
   from pydantic import BaseModel, Field

   class GpuReport(BaseModel):
       nvml_uuid: str
       gpu_index: int
       model_name: str
       vram_total_mb: int = Field(gt=0)
       compute_capability: str | None = None
       mig_capable: bool = False
       mig_enabled_on_parent: bool = False
       mig_profile: str | None = None
       parent_nvml_uuid: str | None = None

   class HostInfo(BaseModel):
       hostname: str
       os: str | None = None
       kernel: str | None = None
       docker_version: str | None = None
       nvidia_driver: str | None = None

   class EngineAvailable(BaseModel):
       name: str
       version: str | None = None
       launcher: str  # 'container:<image-ref>' or 'subprocess:<python> <module>'

   class RegisterRequest(BaseModel):
       agent_version: str
       agent_runtime_mode: Literal["docker", "systemd"]
       host_info: HostInfo
       engines_available: list[EngineAvailable] = []
       gpus: list[GpuReport]

   class ResolvedConfigForAgent(BaseModel):
       hot_tier_path: str
       vault_mount_path: str | None
       eviction_policy_type: Literal["percent_free", "absolute_free"]
       eviction_threshold: float
       auto_iteration_retry_budget: int

   class RegisterResponse(BaseModel):
       endpoint_id: str
       resolved_config: ResolvedConfigForAgent
       stream_url: str  # ws[s]://.../agent/v1/stream
   ```

3. **Write `services/gpu_inventory.py`:**
   ```python
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select, delete
   from datetime import datetime, timezone
   from ..models.fleet import Endpoint, GpuResource

   async def reconcile_endpoint_gpus(
       db: AsyncSession, endpoint: Endpoint, reported: list[dict]
   ) -> None:
       """
       Replace the stored gpu_resource rows for this endpoint with what the agent reports.
       Strategy: upsert by (endpoint_id, nvml_uuid); delete any prior rows not in the report.

       `reported` is a list of dicts shaped like GpuReport.model_dump().
       """
       existing = (await db.execute(
           select(GpuResource).where(GpuResource.endpoint_id == endpoint.id)
       )).scalars().all()
       existing_by_uuid = {g.nvml_uuid: g for g in existing}
       reported_uuids = {g["nvml_uuid"] for g in reported}

       now = datetime.now(timezone.utc)
       for g in reported:
           existing_row = existing_by_uuid.get(g["nvml_uuid"])
           if existing_row is None:
               db.add(GpuResource(endpoint_id=endpoint.id, last_reported_at=now, **g))
           else:
               for k, v in g.items():
                   setattr(existing_row, k, v)
               existing_row.last_reported_at = now

       to_remove = [uuid for uuid in existing_by_uuid if uuid not in reported_uuids]
       if to_remove:
           await db.execute(
               delete(GpuResource).where(
                   GpuResource.endpoint_id == endpoint.id,
                   GpuResource.nvml_uuid.in_(to_remove),
               )
           )
   ```

4. **Write `register.py`:**
   ```python
   from datetime import datetime, timezone
   from fastapi import APIRouter, Depends, HTTPException, status
   from sqlalchemy.ext.asyncio import AsyncSession
   from ...config import get_settings
   from ...db import get_db
   from ...services.resolved_config import resolve_for_endpoint
   from ...services.gpu_inventory import reconcile_endpoint_gpus
   from .dependencies import get_authenticated_agent, AgentPrincipal
   from .schemas import RegisterRequest, RegisterResponse, ResolvedConfigForAgent

   router = APIRouter()

   @router.post("/register", response_model=RegisterResponse)
   async def register_agent(
       payload: RegisterRequest,
       principal: AgentPrincipal = Depends(get_authenticated_agent),
       db: AsyncSession = Depends(get_db),
   ) -> RegisterResponse:
       endpoint = principal.endpoint
       token = principal.token

       # Idempotency: an agent can re-register (e.g., after restart). If consumed_at is already set,
       # we still allow re-registration; we just don't flip the flag again.
       now = datetime.now(timezone.utc)
       if token.consumed_at is None:
           token.consumed_at = now

       endpoint.agent_version = payload.agent_version
       endpoint.agent_runtime_mode = payload.agent_runtime_mode
       endpoint.agent_status = "online"
       endpoint.last_heartbeat_at = now

       await reconcile_endpoint_gpus(db, endpoint, [g.model_dump() for g in payload.gpus])
       await db.commit()
       await db.refresh(endpoint)

       resolved = await resolve_for_endpoint(db, endpoint)
       settings = get_settings()
       # Determine ws vs wss based on the request scheme? Hard without the request object — use settings.
       stream_url = f"{settings.public_url_ws}/agent/v1/stream"

       return RegisterResponse(
           endpoint_id=str(endpoint.id),
           resolved_config=ResolvedConfigForAgent(
               hot_tier_path=resolved.hot_tier_path,
               vault_mount_path=resolved.vault_mount_path,
               eviction_policy_type=resolved.eviction_policy_type,
               eviction_threshold=resolved.eviction_threshold,
               auto_iteration_retry_budget=resolved.auto_iteration_retry_budget,
           ),
           stream_url=stream_url,
       )
   ```

5. **Add a settings field for the public WS URL.** In `config.py`, add:
   ```python
   public_url_ws: str = Field("ws://localhost:8000", alias="KRELIX_PUBLIC_URL_WS")
   public_url_http: str = Field("http://localhost:8000", alias="KRELIX_PUBLIC_URL_HTTP")
   ```
   Update `.env.example` accordingly. The install-instructions builder in T023 should also be updated to use `public_url_http` instead of constructing a URL ad-hoc — if T023 didn't already add this, do it now and note in completion summary.

6. **Wire `agent_v1` router** in `api/agent/v1/router.py`:
   ```python
   from fastapi import APIRouter
   from .register import router as register_router

   agent_v1 = APIRouter(prefix="/agent/v1")
   agent_v1.include_router(register_router, tags=["agent"])
   ```
   Include in `main.py` `create_app()`: `app.include_router(agent_v1)`.

7. **Write `tests/test_agent_auth.py`**:
   - Request without `Authorization` header → 401 `missing_bearer_token`.
   - Request with `Authorization: Bearer invalid` → 401 `invalid_token`.
   - Request with a revoked token → 401 `invalid_token`.
   - Request whose endpoint is soft-deleted → 401 `endpoint_gone`.
   - Valid token returns the right `AgentPrincipal` (endpoint + token rows match).

8. **Write `tests/test_gpu_inventory.py`**:
   - Empty initial state + report of 2 GPUs → 2 rows created.
   - Second report of the same 2 GPUs (with one VRAM value changed) → existing rows updated, no new rows.
   - Third report drops one of the GPUs → that row deleted.
   - MIG fields are stored correctly when present.

9. **Write `tests/test_agent_register_api.py`** (integration):
   - Setup: create an endpoint via the operator API to get a token plaintext.
   - POST `/agent/v1/register` with the token + sample payload → 200 with the right response shape; `consumed_at` is set; endpoint row reflects `agent_status='online'`, `agent_version`, `agent_runtime_mode`; gpu_resource rows exist.
   - Second registration (agent restart simulation) → 200 again; `consumed_at` unchanged; gpu inventory re-reconciled.
   - Token revoked between calls → second registration → 401.
   - CSRF is NOT required (verify by not setting any CSRF cookie/header).
   - Invalid `agent_runtime_mode` (e.g., "kubernetes") → 422.

## Acceptance Criteria

- [ ] `AgentPrincipal` dependency exists, used by HTTP routes via `get_authenticated_agent`.
- [ ] A separate but symmetric lookup is exposed for WebSocket auth (`_lookup_principal` is shared; T025 wires the WS-specific dependency).
- [ ] `POST /agent/v1/register` accepts the documented request shape and returns the documented response shape.
- [ ] Registration is idempotent — agent restart re-registers cleanly without flipping `consumed_at` back.
- [ ] On successful registration, the endpoint row is updated and `gpu_resource` rows are reconciled (upsert + delete-missing).
- [ ] Revoked tokens fail registration with 401 `invalid_token`.
- [ ] CSRF middleware does NOT block `/agent/v1/register` (verified by tests).
- [ ] `resolved_config` in the response reflects merge of globals + per-endpoint overrides.
- [ ] `stream_url` in the response uses `KRELIX_PUBLIC_URL_WS` from settings.
- [ ] All tests green; mypy clean.

## Out of Scope (for this ticket)

- The WebSocket stream itself — T025
- Periodic heartbeat updates to `last_heartbeat_at` from the agent — T025 (heartbeat frame)
- Agent-side code that actually calls this endpoint — T028+ (Phase 5)
- Re-registration token rotation — operator-initiated only in v1 (via T023's regenerate-token endpoint)

## Notes

- The "idempotent registration" behavior is important — agents will restart routinely (host reboot, version upgrade, transient failure). Each restart should re-register without operator intervention.
- The `engines_available` field is stored on the endpoint row? No — there's no column for it in `data-model.md`. For v1, we accept the report but only log it (structlog info event). Storing this is a v2 concern when we add Ollama / llama.cpp / etc. and need to know per-host what's available.
- The "delete missing GPUs" behavior in `reconcile_endpoint_gpus` is correct only when the agent reports its **full** GPU set, not a delta. The agent contract is "always send the complete inventory." Document this clearly in the agent's docstring when T028 builds it.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
