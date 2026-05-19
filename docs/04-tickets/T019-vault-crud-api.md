# T019 — Vault CRUD API

**Status:** Not started
**Phase:** 3 — Vault, settings, HF credential management
**Estimated session length:** 2 hr
**Depends on:** T010, T011, T014, T015
**Blocks:** T022 (frontend), T024-era (endpoint registration references vaults)
**Maps to:** `api-contracts.md` "Vaults" section; `data-model.md` `vault` entity.

---

## Objective

Implement the five Vault endpoints: `GET /api/v1/vaults`, `POST /api/v1/vaults`, `GET /api/v1/vaults/{id}`, `PATCH /api/v1/vaults/{id}`, `DELETE /api/v1/vaults/{id}`. Soft-delete on DELETE; reject DELETE if any active endpoint or the global default still references the vault.

## Context

Vaults are operator-defined storage references. The vault filesystem itself is operator-managed (NFS export, local NVMe directory) — Krelix only stores the **mount path** that host agents expect. Multiple vaults can exist; each `endpoint` (or the `global_settings` default) references one by `vault_id`.

## Read for context

- [`../03-technical/api-contracts.md`](../03-technical/api-contracts.md) — Vaults section
- [`../03-technical/data-model.md`](../03-technical/data-model.md) — `vault` entity + relationships
- [`T010-sqlalchemy-orm-models.md`](T010-sqlalchemy-orm-models.md) — `Vault` model (soft-deletable)

## Files to create

- `backend/src/krelix/api/v1/vaults.py` — router
- `backend/src/krelix/api/v1/schemas/vault.py` — `VaultResponse`, `VaultCreateRequest`, `VaultPatchRequest`, `VaultListResponse`
- `backend/tests/test_vault_api.py` — integration tests

## Files to modify

- `backend/src/krelix/api/v1/router.py` — include the vaults router

## Files to NOT touch

- ORM models, migrations
- Settings or HF credential routers (T017, T018)

## Steps

1. **Write `schemas/vault.py`:**
   ```python
   from pydantic import BaseModel, Field

   class VaultResponse(BaseModel):
       id: str
       name: str
       description: str | None
       mount_path: str
       created_at: str
       updated_at: str

   class VaultListResponse(BaseModel):
       items: list[VaultResponse]
       total: int

   class VaultCreateRequest(BaseModel):
       name: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9 _.-]+$")
       description: str | None = Field(default=None, max_length=512)
       mount_path: str = Field(min_length=1, max_length=512, pattern=r"^/")

   class VaultPatchRequest(BaseModel):
       name: str | None = Field(default=None, min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9 _.-]+$")
       description: str | None = Field(default=None, max_length=512)
       mount_path: str | None = Field(default=None, min_length=1, max_length=512, pattern=r"^/")
   ```

2. **Write `vaults.py`** with five routes. Key behaviors:

   **`GET /api/v1/vaults`** — list non-soft-deleted vaults ordered by name; basic pagination via `limit` / `cursor` query params. For v1 with a small vault count (likely 1–3 per operator), the cursor can be a simple `last_seen_id` based scheme — or skip cursor and just return all rows up to `limit` (default 25, max 100). **Default to no-cursor for v1** — operators won't have hundreds of vaults; keep code simple.

   **`POST /api/v1/vaults`** — create. Check name uniqueness (excluding soft-deleted): if a non-deleted row exists with this name, return 409 `vault_name_taken`. Return 201 with the created row + a `Location` header.

   **`GET /api/v1/vaults/{id}`** — fetch. 404 if soft-deleted or non-existent.

   **`PATCH /api/v1/vaults/{id}`** — partial update. If `name` is being changed, re-check uniqueness against active rows. 409 on conflict.

   **`DELETE /api/v1/vaults/{id}`** — soft delete (set `deleted_at`). Before deleting, check:
   - Any active `endpoint` row with `vault_id == this.id` → return 409 `vault_in_use_by_endpoint` with the endpoint name(s) in `details`.
   - `global_settings.default_vault_id == this.id` → return 409 `vault_in_use_by_globals`.
   - Otherwise soft-delete and return 204.

3. **Update `router.py`** to include vaults under `/vaults`.

4. **Write `tests/test_vault_api.py`:**
   - All endpoints require auth.
   - POST creates a vault; GET list shows it.
   - POST with `mount_path: "relative-path"` → 422 (must start with `/`).
   - POST with duplicate name → 409.
   - PATCH updates name and mount_path; PATCH with empty body → 200, no changes.
   - DELETE a vault not in use → 204; subsequent GET → 404.
   - DELETE after soft-delete: another POST with the same name → 201 (name freed up because uniqueness only checks active rows). **Important to test** — partial unique index from T011 should make this work.
   - DELETE vault that's `default_vault_id` in globals → 409 `vault_in_use_by_globals`.
   - PATCH a soft-deleted vault → 404.
   - All mutating endpoints without CSRF → 403.

## Acceptance Criteria

- [ ] All five endpoints exist under `/api/v1/vaults` with auth required.
- [ ] POST returns 201 with `Location` header and the created vault.
- [ ] Vault name uniqueness is enforced against active (non-soft-deleted) rows only; deleting and recreating with the same name works.
- [ ] PATCH validates the same constraints as POST for any provided fields.
- [ ] DELETE returns 204 on success, 409 with a specific error code if the vault is in use by any endpoint or by the global default.
- [ ] Soft-deleted vaults are not returned by GET list or GET by id.
- [ ] All mutating verbs without CSRF → 403.
- [ ] `mount_path` must be absolute (start with `/`).
- [ ] Pagination is implemented as a `limit` (default 25, max 100) param; cursor is deferred to a future ticket and explicitly documented in the response (omit `next_cursor` for v1, or always set it to `null`).
- [ ] Tests green; mypy clean.

## Out of Scope (for this ticket)

- Vault filesystem verification (does the path actually exist on the relevant hosts?) — that's the host agent's concern at deployment time, not the control plane's concern at vault-CRUD time.
- Frontend — T022.
- Hard delete — soft delete is enough for v1.
- Vault-to-endpoint reassignment helpers — operator does this via the endpoint PATCH endpoint (T024-era).

## Notes

- Partial unique index on `vault.name` where `deleted_at IS NULL` was added in T011's migration. Verify it exists; if not, fall back to an application-level uniqueness check (slower but works).
- The "vault in use" check is read-only — it doesn't need to lock. Race condition where someone assigns a vault to an endpoint between the check and the delete is acceptable in v1 (single operator).

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
