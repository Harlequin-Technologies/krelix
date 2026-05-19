# T018 — HF credential API (GET/PUT/DELETE /api/v1/settings/huggingface)

**Status:** Not started
**Phase:** 3 — Vault, settings, HF credential management
**Estimated session length:** 1.5 hr
**Depends on:** T011, T012, T014, T015
**Blocks:** T021 (frontend), Phase 5+ (host agent uses the token via control plane)
**Maps to:** `api-contracts.md` "HuggingFace credential" section; `data-model.md` `huggingface_credential`; `auth-and-security.md` HF token encryption posture.

---

## Objective

Implement three endpoints for managing the operator's HuggingFace token: `GET /api/v1/settings/huggingface` (returns `{has_token, label, updated_at}` — never the token value), `PUT /api/v1/settings/huggingface` (stores the token AES-256-GCM encrypted), `DELETE /api/v1/settings/huggingface` (clears it). All require auth + CSRF.

## Context

`huggingface_credential` is a singleton row (id=1). Token is encrypted at rest via `encrypt_hf_token` (T012). The row is created lazily on first PUT — no seed migration. The token plaintext is never returned via the API, never logged, and never stored in plaintext at rest.

## Read for context

- [`../03-technical/api-contracts.md`](../03-technical/api-contracts.md) — HuggingFace credential section
- [`../03-technical/auth-and-security.md`](../03-technical/auth-and-security.md) — HF token at-rest encryption
- [`T012-crypto-utilities.md`](T012-crypto-utilities.md) — `encrypt_hf_token`, `decrypt_hf_token`

## Files to create

- `backend/src/krelix/api/v1/settings_hf.py` — the router
- `backend/src/krelix/api/v1/schemas/hf.py` — `HfCredentialStatusResponse`, `HfCredentialPutRequest`
- `backend/src/krelix/services/hf_credential.py` — small service for get/set/delete (used by future tickets too — e.g., when the agent needs the token, the control plane reads + decrypts via this service)
- `backend/tests/test_hf_credential_api.py`
- `backend/tests/test_hf_credential_service.py`

## Files to modify

- `backend/src/krelix/api/v1/router.py` — include the new router under `/settings`

## Files to NOT touch

- `crypto.py` (T012)
- ORM models (T010), migrations (T011)

## Steps

1. **Write `schemas/hf.py`:**
   ```python
   from pydantic import BaseModel, Field

   class HfCredentialStatusResponse(BaseModel):
       has_token: bool
       label: str | None
       updated_at: str | None  # ISO

   class HfCredentialPutRequest(BaseModel):
       token: str = Field(min_length=8, max_length=512, pattern=r"^[A-Za-z0-9_\-.]+$")
       label: str | None = Field(default=None, max_length=128)
   ```

   - HF tokens currently follow `hf_...` patterns; the regex is permissive enough to accept future formats without being a free-for-all.

2. **Write `services/hf_credential.py`:**
   ```python
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select
   from ..crypto import encrypt_hf_token, decrypt_hf_token
   from ..models.storage import HuggingFaceCredential

   class HfCredentialService:
       def __init__(self, db: AsyncSession) -> None:
           self.db = db

       async def get_status(self) -> dict:
           row = await self._row()
           if row is None:
               return {"has_token": False, "label": None, "updated_at": None}
           return {
               "has_token": True,
               "label": row.label,
               "updated_at": row.updated_at.isoformat(),
           }

       async def get_token_plaintext(self) -> str | None:
           """Used by internal callers that need the actual token (downloads, agent commands)."""
           row = await self._row()
           if row is None:
               return None
           return decrypt_hf_token(row.token_encrypted)

       async def upsert(self, token: str, label: str | None) -> None:
           ciphertext = encrypt_hf_token(token)
           row = await self._row()
           if row is None:
               row = HuggingFaceCredential(id=1, token_encrypted=ciphertext, label=label)
               self.db.add(row)
           else:
               row.token_encrypted = ciphertext
               row.label = label
           await self.db.commit()

       async def delete(self) -> bool:
           row = await self._row()
           if row is None:
               return False
           await self.db.delete(row)
           await self.db.commit()
           return True

       async def _row(self) -> HuggingFaceCredential | None:
           result = await self.db.execute(
               select(HuggingFaceCredential).where(HuggingFaceCredential.id == 1)
           )
           return result.scalar_one_or_none()
   ```

3. **Write `settings_hf.py`:**
   ```python
   from fastapi import APIRouter, Depends, Response, status
   from sqlalchemy.ext.asyncio import AsyncSession
   from ...db import get_db
   from ...auth.dependencies import get_current_admin_user
   from ...models.auth import AdminUser
   from ...services.hf_credential import HfCredentialService
   from .schemas.hf import HfCredentialStatusResponse, HfCredentialPutRequest

   router = APIRouter()

   @router.get("/huggingface", response_model=HfCredentialStatusResponse)
   async def get_hf(
       _: AdminUser = Depends(get_current_admin_user),
       db: AsyncSession = Depends(get_db),
   ) -> HfCredentialStatusResponse:
       return HfCredentialStatusResponse(**await HfCredentialService(db).get_status())

   @router.put("/huggingface", status_code=status.HTTP_204_NO_CONTENT)
   async def put_hf(
       payload: HfCredentialPutRequest,
       _: AdminUser = Depends(get_current_admin_user),
       db: AsyncSession = Depends(get_db),
   ) -> Response:
       await HfCredentialService(db).upsert(payload.token, payload.label)
       return Response(status_code=status.HTTP_204_NO_CONTENT)

   @router.delete("/huggingface", status_code=status.HTTP_204_NO_CONTENT)
   async def delete_hf(
       _: AdminUser = Depends(get_current_admin_user),
       db: AsyncSession = Depends(get_db),
   ) -> Response:
       await HfCredentialService(db).delete()
       return Response(status_code=status.HTTP_204_NO_CONTENT)
   ```

4. **Update `api/v1/router.py`** to include the new router under `/settings` (next to T017's `settings_global`).

5. **Write `tests/test_hf_credential_service.py`:**
   - `get_status()` on a clean DB returns `{has_token: False, label: None, updated_at: None}`.
   - `upsert("hf_abc", "my-token")` then `get_status()` returns `has_token=True`, correct label, recent updated_at.
   - `get_token_plaintext()` returns `"hf_abc"` (round-trip through encrypt+decrypt).
   - `upsert("hf_xyz", None)` overwrites; `get_token_plaintext()` returns `"hf_xyz"`.
   - `delete()` returns True; subsequent `get_status()` returns `has_token=False`.
   - `delete()` on empty returns False.

6. **Write `tests/test_hf_credential_api.py`:**
   - All three endpoints require auth (unauthenticated → 401).
   - PUT validates token regex (rejects `"with spaces"`, accepts `"hf_abc.123-XYZ_2"`).
   - PUT without CSRF → 403.
   - PUT then GET → `has_token=True`.
   - DELETE then GET → `has_token=False`.
   - GET never returns the token plaintext in the response body (verify the response text does not contain the input token value).
   - Audit: the request to PUT does not log the token value (search the test's log capture for the input token — it should be absent or `<redacted>`).

7. **Verify:**
   - `uv run pytest` green.
   - `uv run mypy` clean.

## Acceptance Criteria

- [ ] All three endpoints exist under `/api/v1/settings/huggingface` and require auth.
- [ ] GET never returns the token plaintext.
- [ ] PUT stores the token AES-256-GCM encrypted via `encrypt_hf_token` from T012; the DB column contains ciphertext (verify directly via a query in a test).
- [ ] PUT validates the token regex and length.
- [ ] PUT without CSRF → 403.
- [ ] DELETE returns 204 whether or not a credential existed.
- [ ] `HfCredentialService.get_token_plaintext()` is available for future internal callers (e.g., the HF download path).
- [ ] Token value does not appear in any structlog output (redaction filter intact).
- [ ] Tests green; mypy clean.

## Out of Scope (for this ticket)

- Frontend — T021.
- Per-user / per-tenant tokens — single-operator v1.
- HF API health check (validating the token by hitting HF) — could be added as a small POST endpoint later; not v1.
- Token rotation reminders / expiry tracking — HF tokens don't expire on a schedule that Krelix would track.

## Notes

- The service class is intentionally lightweight — it's not a full repository pattern. If multiple tickets end up using it heavily, that's the right place to refactor.
- `get_token_plaintext()` is the one method that callers should treat as "I am about to do something sensitive." Wrap its usage in a clear log line (e.g., `logger.info("hf_token_accessed", purpose="model_download")`) at call sites — not in the service itself.
- The DB column is `LargeBinary` (BYTEA). When testing direct DB reads, the value should be raw bytes, not a string.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
