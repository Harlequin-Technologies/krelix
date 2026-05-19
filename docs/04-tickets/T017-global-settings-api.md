# T017 — Global settings API (GET/PATCH /api/v1/settings/global)

**Status:** Not started
**Phase:** 3 — Vault, settings, HF credential management
**Estimated session length:** 1.5 hr
**Depends on:** T011, T014, T015
**Blocks:** T021 (frontend settings page); T024-era (endpoint registration uses resolved config)
**Maps to:** `api-contracts.md` "Global settings" section; `data-model.md` `global_settings` entity.

---

## Objective

Implement `GET /api/v1/settings/global` (returns the seeded singleton row) and `PATCH /api/v1/settings/global` (updates fields). Both endpoints require auth.

## Context

`global_settings` is a singleton row (id=1) seeded by the `0002_seed_defaults` migration in T011. Every endpoint registration resolves config by reading per-endpoint overrides falling back to these globals. The PATCH endpoint accepts any subset of fields; absent fields are unchanged.

## Read for context

- [`../03-technical/api-contracts.md`](../03-technical/api-contracts.md) — Global settings section
- [`../03-technical/data-model.md`](../03-technical/data-model.md) — `global_settings` entity
- [`T016-auth-api-endpoints.md`](T016-auth-api-endpoints.md) — established router + schemas pattern

## Files to create

- `backend/src/krelix/api/v1/settings_global.py` — router with 2 endpoints
- `backend/src/krelix/api/v1/schemas/settings.py` — `GlobalSettingsResponse`, `GlobalSettingsPatchRequest`
- `backend/tests/test_settings_global_api.py` — integration tests

## Files to modify

- `backend/src/krelix/api/v1/router.py` — include the new router under `/settings`

## Files to NOT touch

- ORM models (T010)
- Migrations (T011)
- HF credential API (T018) — separate ticket

## Steps

1. **Write `schemas/settings.py`:**
   ```python
   from typing import Literal
   from pydantic import BaseModel, Field

   EvictionPolicyType = Literal["percent_free", "absolute_free"]

   class GlobalSettingsResponse(BaseModel):
       default_hot_tier_path: str
       default_vault_id: str | None
       eviction_policy_type: EvictionPolicyType
       eviction_threshold: float
       auto_iteration_retry_budget: int
       updated_at: str  # ISO timestamp

   class GlobalSettingsPatchRequest(BaseModel):
       default_hot_tier_path: str | None = None
       default_vault_id: str | None = None  # NULL means "no default vault"
       eviction_policy_type: EvictionPolicyType | None = None
       eviction_threshold: float | None = Field(default=None, gt=0)
       auto_iteration_retry_budget: int | None = Field(default=None, ge=1, le=20)
   ```

   - `default_vault_id` is interesting: distinguishing "not provided" from "explicitly NULL" requires a sentinel. For v1 simplicity, treat absent as "no change" and explicit `null` in the JSON body as "clear the value." Implementation can use `model_dump(exclude_unset=True)` on the request to distinguish — this is the recommended Pydantic v2 approach for partial updates.

2. **Write `settings_global.py`:**
   ```python
   from fastapi import APIRouter, Depends, HTTPException, status
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select
   from ...db import get_db
   from ...auth.dependencies import get_current_admin_user
   from ...models.storage import GlobalSettings, Vault
   from ...models.auth import AdminUser
   from .schemas.settings import GlobalSettingsResponse, GlobalSettingsPatchRequest

   router = APIRouter()

   @router.get("/global", response_model=GlobalSettingsResponse)
   async def get_global_settings(
       _: AdminUser = Depends(get_current_admin_user),
       db: AsyncSession = Depends(get_db),
   ) -> GlobalSettingsResponse:
       result = await db.execute(select(GlobalSettings).where(GlobalSettings.id == 1))
       row = result.scalar_one()
       return GlobalSettingsResponse(
           default_hot_tier_path=row.default_hot_tier_path,
           default_vault_id=str(row.default_vault_id) if row.default_vault_id else None,
           eviction_policy_type=row.eviction_policy_type,
           eviction_threshold=row.eviction_threshold,
           auto_iteration_retry_budget=row.auto_iteration_retry_budget,
           updated_at=row.updated_at.isoformat(),
       )

   @router.patch("/global", response_model=GlobalSettingsResponse)
   async def patch_global_settings(
       payload: GlobalSettingsPatchRequest,
       _: AdminUser = Depends(get_current_admin_user),
       db: AsyncSession = Depends(get_db),
   ) -> GlobalSettingsResponse:
       updates = payload.model_dump(exclude_unset=True)
       # If default_vault_id is being set non-null, verify the vault exists and isn't soft-deleted
       if updates.get("default_vault_id") is not None:
           vault_id = updates["default_vault_id"]
           v = await db.execute(
               select(Vault).where(Vault.id == vault_id, Vault.deleted_at.is_(None))
           )
           if v.scalar_one_or_none() is None:
               raise HTTPException(
                   status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                   detail={"error": {"code": "vault_not_found",
                                       "message": f"Vault {vault_id} does not exist."}},
               )
       result = await db.execute(select(GlobalSettings).where(GlobalSettings.id == 1))
       row = result.scalar_one()
       for k, v in updates.items():
           setattr(row, k, v)
       await db.commit()
       await db.refresh(row)
       return GlobalSettingsResponse(  # same shape as GET
           default_hot_tier_path=row.default_hot_tier_path,
           default_vault_id=str(row.default_vault_id) if row.default_vault_id else None,
           eviction_policy_type=row.eviction_policy_type,
           eviction_threshold=row.eviction_threshold,
           auto_iteration_retry_budget=row.auto_iteration_retry_budget,
           updated_at=row.updated_at.isoformat(),
       )
   ```

   - Consider extracting the response-building into a small helper if it gets repeated more than 2x (which here it does, marginally).

3. **Update `api/v1/router.py`:**
   ```python
   from .settings_global import router as settings_global_router
   api_v1.include_router(settings_global_router, prefix="/settings", tags=["settings"])
   ```

4. **Write `tests/test_settings_global_api.py`** (integration):
   - Unauthenticated GET → 401.
   - Authenticated GET → 200 with the seeded defaults.
   - PATCH eviction_threshold = 25.0 → 200, GET reflects it.
   - PATCH default_vault_id = "<non-existent-uuid>" → 422.
   - PATCH eviction_threshold = -5 → 422 (Pydantic `gt=0`).
   - PATCH auto_iteration_retry_budget = 0 → 422 (`ge=1`).
   - PATCH empty body → 200, no fields changed.
   - PATCH without CSRF cookie/header → 403 (verifies CSRF wiring still works).

## Acceptance Criteria

- [ ] `GET /api/v1/settings/global` returns the singleton row with auth required.
- [ ] `PATCH /api/v1/settings/global` accepts partial updates, validates fields, and rejects unknown vault IDs.
- [ ] Eviction threshold must be > 0; retry budget must be 1–20; eviction policy type is constrained to the two allowed strings.
- [ ] Unauthenticated requests → 401.
- [ ] PATCH without CSRF → 403.
- [ ] All routes use the conventional error response shape.
- [ ] `uv run mypy` clean; tests green.

## Out of Scope (for this ticket)

- Frontend UI — T021.
- Per-endpoint overrides — endpoints have their own override fields (set via the endpoint PATCH, T024-era).
- Audit logging of settings changes — implied future need; not v1.
- Resetting to defaults — operator does this via PATCH with the seeded defaults; no convenience endpoint.

## Notes

- Use `model_dump(exclude_unset=True)` for the partial-update pattern. Don't use `.dict()` (Pydantic v1).
- The vault-existence check on PATCH is the only cross-table reference. Keep it simple.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
