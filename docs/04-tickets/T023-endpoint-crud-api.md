# T023 — Endpoint CRUD API + resolved-config helper

**Status:** Not started
**Phase:** 4 — Endpoint registration + agent bootstrap protocol
**Estimated session length:** 3.5 hr
**Depends on:** T010, T011, T014, T015, T017
**Blocks:** T024, T026
**Maps to:** `api-contracts.md` "Endpoints (GPU hosts)" section; `data-model.md` `endpoint` + override fields; `architecture.md` "Configuration Model (Globals + Overrides)".

---

## Objective

Implement the endpoint CRUD endpoints: list, create (with one-time token issuance), get (including resolved config and GPU summary), patch (overrides), delete (with active-deployment safety check), regenerate-token, and GET endpoints/{id}/gpus. Also lands a small **resolved-config helper** that merges per-endpoint overrides with global defaults — used here and by T024 when responding to agent registration.

## Context

Endpoint registration is a two-step dance: the operator creates an endpoint row via this API (receiving a one-time bearer token), then runs the agent on the GPU host pointed at the control plane with that token. The token is only readable in the API response **once** — afterwards only the SHA-256 hash is stored. The endpoint's effective config is resolved from `global_settings` overlaid with per-endpoint nullable override fields. This same resolution logic is shared with the agent registration endpoint (T024), so it lives in a helper module.

## Read for context

- [`../03-technical/api-contracts.md`](../03-technical/api-contracts.md) — Endpoints section in full
- [`../03-technical/architecture.md`](../03-technical/architecture.md) — "Configuration Model (Globals + Overrides)"
- [`../03-technical/data-model.md`](../03-technical/data-model.md) — `endpoint` + `agent_registration_token`
- [`T010-sqlalchemy-orm-models.md`](T010-sqlalchemy-orm-models.md) — models
- [`T017-global-settings-api.md`](T017-global-settings-api.md) — global settings shape

## Files to create

- `backend/src/krelix/api/v1/endpoints.py` — the router (7 endpoints)
- `backend/src/krelix/api/v1/schemas/endpoint.py` — request/response schemas
- `backend/src/krelix/services/resolved_config.py` — small helper module
- `backend/src/krelix/services/agent_tokens.py` — small helper: generate plaintext + hash, revoke, regenerate
- `backend/tests/test_endpoint_api.py`
- `backend/tests/test_resolved_config.py`
- `backend/tests/test_agent_tokens.py`

## Files to modify

- `backend/src/krelix/api/v1/router.py` — include the endpoints router under `/endpoints`

## Files to NOT touch

- ORM models, migrations
- Agent surface (`/agent/v1/...`) — T024+
- Vault / settings / HF credential routers — Phase 3, finalized

## Steps

1. **Write `services/agent_tokens.py`:**
   ```python
   import hashlib
   import secrets
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select
   from ..models.auth import AgentRegistrationToken

   TOKEN_PREFIX = "krelix_agt_"

   def generate_token_plaintext() -> str:
       return TOKEN_PREFIX + secrets.token_urlsafe(32)

   def hash_token(plaintext: str) -> str:
       return hashlib.sha256(plaintext.encode()).hexdigest()

   async def create_token(db: AsyncSession, *, label: str) -> tuple[AgentRegistrationToken, str]:
       """Returns (row, plaintext). Caller must commit the session."""
       plaintext = generate_token_plaintext()
       row = AgentRegistrationToken(token_hash=hash_token(plaintext), label=label)
       db.add(row)
       await db.flush()  # populate row.id without committing yet
       return row, plaintext

   async def revoke_token(db: AsyncSession, token_id) -> None:
       row = (await db.execute(
           select(AgentRegistrationToken).where(AgentRegistrationToken.id == token_id)
       )).scalar_one()
       row.revoked_at = func.now()  # use SQL now; or datetime.now(timezone.utc)
   ```

2. **Write `services/resolved_config.py`:**
   ```python
   from dataclasses import dataclass
   from uuid import UUID
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select
   from ..models.storage import GlobalSettings, Vault
   from ..models.fleet import Endpoint

   @dataclass
   class ResolvedConfig:
       hot_tier_path: str
       vault_id: UUID | None
       vault_mount_path: str | None
       eviction_policy_type: str
       eviction_threshold: float
       auto_iteration_retry_budget: int

   async def resolve_for_endpoint(db: AsyncSession, endpoint: Endpoint) -> ResolvedConfig:
       gs = (await db.execute(select(GlobalSettings).where(GlobalSettings.id == 1))).scalar_one()
       vault_id = endpoint.vault_id if endpoint.vault_id is not None else gs.default_vault_id
       vault_mount_path = None
       if vault_id is not None:
           v = (await db.execute(
               select(Vault).where(Vault.id == vault_id, Vault.deleted_at.is_(None))
           )).scalar_one_or_none()
           vault_mount_path = v.mount_path if v else None
       return ResolvedConfig(
           hot_tier_path=endpoint.hot_tier_path or gs.default_hot_tier_path,
           vault_id=vault_id,
           vault_mount_path=vault_mount_path,
           eviction_policy_type=endpoint.eviction_policy_type or gs.eviction_policy_type,
           eviction_threshold=endpoint.eviction_threshold if endpoint.eviction_threshold is not None else gs.eviction_threshold,
           auto_iteration_retry_budget=endpoint.auto_iteration_retry_budget or gs.auto_iteration_retry_budget,
       )
   ```

3. **Write `schemas/endpoint.py`** with `EndpointCreateRequest`, `EndpointPatchRequest`, `EndpointResponse` (includes nested `resolved_config` and `gpu_summary`), `EndpointListResponse`, `EndpointCreatedResponse` (includes the plaintext token + install instructions string), `GpuResourceResponse`, `EndpointGpusResponse`, `RegenerateTokenResponse`.

4. **Write `endpoints.py`** with all 7 routes. Key implementation notes:

   **`POST /api/v1/endpoints`:**
   - Validate request via `EndpointCreateRequest` (name regex `[a-z0-9-]+`, hostname is a valid FQDN, override fields validated like the global settings PATCH).
   - Check name uniqueness (active rows) → 409 `endpoint_name_taken`.
   - Check hostname uniqueness (active rows) → 409 `hostname_in_use`.
   - If `vault_id` override provided, verify it exists → 422 `vault_not_found`.
   - In a single transaction:
     - Generate token via `services/agent_tokens.create_token(db, label=f"{name} bootstrap")` → get the row + plaintext.
     - Create Endpoint row with `registration_token_id` set, `agent_status='never_connected'`, override fields from request.
     - Commit.
   - Build install instructions string — two snippets (docker-compose for container mode, systemd unit env for bare-metal mode). See "Install Instructions Format" below.
   - Return 201 with `EndpointCreatedResponse` including the plaintext token and install_instructions. **Plaintext returned only here.**

   **`POST /api/v1/endpoints/{id}/regenerate-token`:**
   - Look up endpoint. 404 if soft-deleted or not found.
   - Revoke the current token (`revoked_at = now()`).
   - Generate a new token; create a new `agent_registration_token` row; update `endpoint.registration_token_id`.
   - Note: the agent's existing WebSocket session, if any, will be invalidated on next auth check. That's intentional — operator regenerated because they wanted to revoke.
   - Return 200 with the new plaintext + install instructions (same shape as creation response, minus the endpoint metadata since the caller already has it).

   **`GET /api/v1/endpoints`:**
   - List active endpoints; include `resolved_config` and `gpu_summary` (a count of GPUs + total/free VRAM aggregated from gpu_resource rows).
   - Pagination: limit/cursor or just limit-only (mirror T019's vault list approach).

   **`GET /api/v1/endpoints/{id}`:**
   - Return endpoint with full `resolved_config` and list of `gpu_resource` rows (not just summary).

   **`PATCH /api/v1/endpoints/{id}`:**
   - Allow `display_name` and the override fields. `name` and `hostname` are immutable (per api-contracts).
   - If `vault_id` is being set non-null, verify it exists.
   - Apply with `model_dump(exclude_unset=True)`.

   **`DELETE /api/v1/endpoints/{id}`:**
   - Check for active deployments (`SELECT 1 FROM deployment WHERE endpoint_id = ? AND status IN ('pending','provisioning','downloading','copying','starting','running')`). If any, return 409 `endpoint_has_active_deployments` with the count.
   - Soft-delete (`deleted_at = now()`). Revoke the associated registration token.
   - Return 204.

   **`GET /api/v1/endpoints/{id}/gpus`:**
   - Return all `gpu_resource` rows for this endpoint, including MIG fields.

5. **Install Instructions Format** — build a single multi-line string for the response. Example:

   ```
   ## Container mode (Docker)
   Save the following as docker-compose.agent.yml on the GPU host, then run:
     docker compose -f docker-compose.agent.yml up -d

   services:
     krelix-agent:
       image: ghcr.io/harlequin-technologies/krelix-agent:latest
       restart: unless-stopped
       runtime: nvidia
       environment:
         KRELIX_CONTROL_URL: https://krelix.dropthe8.com
         KRELIX_AGENT_TOKEN: <PASTE TOKEN HERE>
         KRELIX_AGENT_RUNTIME_MODE: docker
       volumes:
         - /var/run/docker.sock:/var/run/docker.sock
         - /var/lib/krelix/hot:/var/lib/krelix/hot
         - /mnt/krelix-vault:/mnt/krelix-vault
       deploy:
         resources:
           reservations:
             devices:
               - driver: nvidia
                 count: all
                 capabilities: [gpu]

   ## Bare-metal mode (systemd)
   1. Install vLLM in a venv at /opt/krelix/engines/vllm (operator-managed).
   2. Create /etc/krelix/agent.env with:
        KRELIX_CONTROL_URL=https://krelix.dropthe8.com
        KRELIX_AGENT_TOKEN=<PASTE TOKEN HERE>
        KRELIX_AGENT_RUNTIME_MODE=systemd
        KRELIX_HOT_TIER_PATH=/var/lib/krelix/hot
        KRELIX_VAULT_MOUNT_PATH=/mnt/krelix-vault
        KRELIX_ENGINE_VLLM_PYTHON=/opt/krelix/engines/vllm/bin/python
        KRELIX_ENGINE_VLLM_MODULE=vllm.entrypoints.openai.api_server
   3. Install the krelix-agent.service unit (see docs/install/host-agent-bare-metal.md).
   4. systemctl enable --now krelix-agent
   ```

   The control plane's own URL is read from a `KRELIX_PUBLIC_URL` env var (add to Settings in T009-amend or here — if not yet there, default to `http://<control-host>:8000` and surface as a TODO). The token placeholder `<PASTE TOKEN HERE>` is in the instructions; the actual token is returned in a separate `token` field, so the frontend can inject it for copy-paste.

6. **Update `router.py`** to include endpoints under `/endpoints`.

7. **Write `tests/test_resolved_config.py`** — verify the merge logic with table-driven test cases: endpoint with no overrides → falls back to all globals; endpoint with hot_tier_path override only → only that field overridden; endpoint with NULL vault override and globals NULL → resolved vault is None; etc.

8. **Write `tests/test_agent_tokens.py`** — token plaintext starts with the prefix; `hash_token` is deterministic; `create_token` writes a row with the hash.

9. **Write `tests/test_endpoint_api.py`** (integration) covering:
   - All routes require auth.
   - POST creates endpoint + returns one-time plaintext token + install instructions.
   - POST with duplicate name / hostname → 409.
   - POST with non-existent vault_id → 422.
   - GET list shows the endpoint with resolved_config reflecting either overrides or globals.
   - PATCH override fields → 200; subsequent GET shows the new resolved_config.
   - PATCH name → 422 (immutable).
   - DELETE with active deployment → 409.
   - DELETE without active deployments → 204; subsequent GET → 404.
   - Regenerate-token → 200 with a different plaintext; previous token's revoked_at is set.
   - GET /endpoints/{id}/gpus → empty list initially (no agent has connected yet).
   - All mutating verbs without CSRF → 403.

## Acceptance Criteria

- [ ] All 7 endpoints exist under `/api/v1/endpoints` with auth required.
- [ ] POST returns `EndpointCreatedResponse` containing endpoint metadata + one-time plaintext token + install_instructions string.
- [ ] Token plaintext is returned exactly once (only in POST and regenerate-token responses); GET / list never return it.
- [ ] Token storage is SHA-256 hashed in `agent_registration_token.token_hash`.
- [ ] `resolve_for_endpoint` correctly merges per-endpoint overrides with globals; falls back element-by-element.
- [ ] `vault_id` resolution honors per-endpoint override (including explicit NULL to clear), with global fallback otherwise.
- [ ] `gpu_summary` in list responses aggregates from gpu_resource rows.
- [ ] DELETE blocks when active deployments exist; succeeds (soft-delete + token revoke) otherwise.
- [ ] Regenerate-token revokes the old token before issuing a new one.
- [ ] Install instructions string includes both Docker Compose and systemd snippets with the token placeholder, hot tier path, vault mount path, and control plane URL all filled in correctly from settings.
- [ ] All mutating verbs require CSRF; auth required on all routes.
- [ ] All tests green; mypy clean.

## Out of Scope (for this ticket)

- Agent registration endpoint — T024
- Agent WebSocket — T025
- Frontend — T026
- Real-time GPU state push — Phase 5 / 11 (D-phase)
- Verifying the install instructions actually deploy a working agent — that's manually tested in Phase 5

## Notes

- `KRELIX_PUBLIC_URL` is needed by the install-instructions builder. If it's not already in Settings (T009), add it here as a new optional Settings field, defaulting to constructing `http://<KRELIX_BIND_HOST>:<KRELIX_BIND_PORT>` if absent. Surface this addition in completion summary.
- The install instructions string is plain text by design — the frontend formats it. Don't return HTML or markdown.
- Consider making `install_instructions` two separate fields (`container_mode_instructions`, `bare_metal_instructions`) for cleaner frontend rendering. Either is fine — pick the cleaner one in implementation.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
