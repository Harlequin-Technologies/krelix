# T014 — Redis-backed session storage + auth dependency

**Status:** Not started
**Phase:** 2 — Database foundation + auth
**Estimated session length:** 2 hr
**Depends on:** T009
**Blocks:** T016
**Maps to:** `auth-and-security.md` "Authentication / Operator surface" (session cookie + Redis-backed storage); `api-contracts.md` (cookie-based auth).

---

## Objective

Implement Redis-backed session storage and the FastAPI dependency that resolves a request's session cookie to an authenticated `AdminUser`. Includes session creation, lookup, refresh, and revocation. Cookies are `HttpOnly` + `SameSite=Lax`, `Secure` when behind TLS (auto-detect via `X-Forwarded-Proto`).

## Context

Session approach per `auth-and-security.md`: opaque 256-bit random session IDs stored in cookies; session data lives in Redis under key `krelix:session:<id>`. Lifetime: 30 days idle, 14-day rolling refresh (refresh the Redis TTL on each request that uses the session). Sessions are revoked by deleting the Redis key (clean logout, and operator-initiated force-logout in the future).

## Read for context

- [`../03-technical/auth-and-security.md`](../03-technical/auth-and-security.md) — "Authentication / Operator surface" subsection
- [`../03-technical/api-contracts.md`](../03-technical/api-contracts.md) — Auth section (cookie name `krelix_session`)
- [`T009-settings-db-redis-connections.md`](T009-settings-db-redis-connections.md) — Redis client
- [`T010-sqlalchemy-orm-models.md`](T010-sqlalchemy-orm-models.md) — `AdminUser` model

## Files to create

- `backend/src/krelix/auth/__init__.py` — empty
- `backend/src/krelix/auth/sessions.py` — `SessionStore` (Redis-backed) + helpers
- `backend/src/krelix/auth/dependencies.py` — FastAPI dependencies: `get_current_admin_user`, `optional_current_admin_user`
- `backend/src/krelix/auth/cookies.py` — cookie set/clear helpers + Secure-flag detection
- `backend/tests/test_sessions.py` — unit tests

## Files to modify

- None outside the new module

## Files to NOT touch

- Auth API routes (T016)
- CSRF middleware (T015)
- `models/auth.py` (T010 — finalized)

## Steps

1. **Write `backend/src/krelix/auth/sessions.py`:**
   ```python
   import secrets
   import json
   from datetime import datetime, timezone
   from uuid import UUID
   from redis.asyncio import Redis

   SESSION_KEY_PREFIX = "krelix:session:"
   SESSION_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days
   SESSION_REFRESH_INTERVAL_SECONDS = 14 * 24 * 60 * 60  # rolling-refresh threshold

   class SessionStore:
       def __init__(self, redis: Redis) -> None:
           self.redis = redis

       async def create(self, *, admin_user_id: UUID) -> str:
           sid = secrets.token_urlsafe(32)  # 256 bits
           payload = {
               "admin_user_id": str(admin_user_id),
               "created_at": datetime.now(timezone.utc).isoformat(),
               "last_seen_at": datetime.now(timezone.utc).isoformat(),
           }
           await self.redis.set(
               SESSION_KEY_PREFIX + sid, json.dumps(payload), ex=SESSION_TTL_SECONDS
           )
           return sid

       async def lookup(self, sid: str) -> dict | None:
           raw = await self.redis.get(SESSION_KEY_PREFIX + sid)
           if not raw:
               return None
           data = json.loads(raw)
           # Refresh TTL on every lookup — rolling refresh
           await self.redis.expire(SESSION_KEY_PREFIX + sid, SESSION_TTL_SECONDS)
           data["last_seen_at"] = datetime.now(timezone.utc).isoformat()
           await self.redis.set(SESSION_KEY_PREFIX + sid, json.dumps(data), ex=SESSION_TTL_SECONDS)
           return data

       async def revoke(self, sid: str) -> None:
           await self.redis.delete(SESSION_KEY_PREFIX + sid)
   ```

2. **Write `backend/src/krelix/auth/cookies.py`:**
   ```python
   from fastapi import Request, Response

   COOKIE_SESSION = "krelix_session"
   COOKIE_CSRF = "krelix_csrf"

   def is_https_request(request: Request) -> bool:
       """True if the request came in via HTTPS, including through a trusted reverse proxy."""
       return (
           request.url.scheme == "https"
           or request.headers.get("x-forwarded-proto", "").lower() == "https"
       )

   def set_session_cookie(response: Response, sid: str, request: Request) -> None:
       response.set_cookie(
           key=COOKIE_SESSION,
           value=sid,
           httponly=True,
           samesite="lax",
           secure=is_https_request(request),
           max_age=30 * 24 * 60 * 60,
           path="/",
       )

   def clear_session_cookie(response: Response, request: Request) -> None:
       response.delete_cookie(
           key=COOKIE_SESSION,
           httponly=True,
           samesite="lax",
           secure=is_https_request(request),
           path="/",
       )
   ```

3. **Write `backend/src/krelix/auth/dependencies.py`:**
   ```python
   from uuid import UUID
   from fastapi import Cookie, Depends, HTTPException, status
   from sqlalchemy.ext.asyncio import AsyncSession
   from sqlalchemy import select
   from ..db import get_db
   from ..redis_client import get_redis
   from ..models.auth import AdminUser
   from .sessions import SessionStore
   from .cookies import COOKIE_SESSION

   async def optional_current_admin_user(
       krelix_session: str | None = Cookie(default=None),
       db: AsyncSession = Depends(get_db),
   ) -> AdminUser | None:
       if not krelix_session:
           return None
       store = SessionStore(get_redis())
       data = await store.lookup(krelix_session)
       if not data:
           return None
       user_id = UUID(data["admin_user_id"])
       result = await db.execute(select(AdminUser).where(AdminUser.id == user_id))
       return result.scalar_one_or_none()

   async def get_current_admin_user(
       current: AdminUser | None = Depends(optional_current_admin_user),
   ) -> AdminUser:
       if current is None:
           raise HTTPException(
               status_code=status.HTTP_401_UNAUTHORIZED,
               detail={"error": {"code": "not_authenticated", "message": "Authentication required."}},
           )
       return current
   ```

4. **Write `backend/tests/test_sessions.py`:**
   - Create a session, look it up, verify data round-trips.
   - Looking up a non-existent SID returns `None`.
   - Revoke deletes the key from Redis.
   - Rolling refresh: lookup a session, verify TTL was reset (read `TTL` directly via Redis).
   - `is_https_request` returns True for `X-Forwarded-Proto: https`, False otherwise.
   - `set_session_cookie` sets `HttpOnly` and `SameSite=Lax` always; `Secure` only when HTTPS.

5. **Verify:**
   - `uv run pytest tests/test_sessions.py` green (integration; needs Redis up).
   - `uv run mypy src/krelix/auth` clean.

## Acceptance Criteria

- [ ] `SessionStore` provides `create`, `lookup`, `revoke` with the documented semantics.
- [ ] Sessions live under `krelix:session:<sid>` keys in Redis with 30-day TTL.
- [ ] Lookup refreshes the TTL (rolling refresh).
- [ ] Cookie helpers set `HttpOnly` + `SameSite=Lax` always; `Secure` when the request is HTTPS (direct or via `X-Forwarded-Proto`).
- [ ] `get_current_admin_user` raises 401 with the conventional error shape when there's no valid session.
- [ ] `optional_current_admin_user` returns `None` rather than raising (used by routes that work for both authenticated and anonymous callers — e.g., the first-run setup flow).
- [ ] Stale session IDs (deleted from Redis) cause both dependencies to behave as if no cookie was sent.
- [ ] `uv run pytest tests/test_sessions.py` green; `uv run mypy` clean.

## Out of Scope (for this ticket)

- The actual auth API routes (`/login`, `/logout`, `/me`, `/setup`) — T016
- CSRF protection — T015
- Login rate limiting — T016
- Password verification — T013 covers it; T016 wires it to login

## Notes

- `secrets.token_urlsafe(32)` yields 43 url-safe base64 characters from 32 bytes = 256 bits of entropy. Don't use `secrets.token_hex` — bigger cookie, no security benefit.
- The session payload is intentionally tiny — just `admin_user_id` and timestamps. Don't tempt yourself to cache the full user object; refetch from DB on each request (it's cheap, and avoids staleness).
- The 14-day rolling refresh threshold isn't enforced separately in this implementation because we refresh on every lookup. If you want to optimize Redis writes, you can compare `last_seen_at` and only refresh if > 1 hour stale — but for v1, the simpler always-refresh approach is fine.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
