# T016 — Auth API (setup, login, logout, me + rate limiting)

**Status:** Not started
**Phase:** 2 — Database foundation + auth
**Estimated session length:** 3 hr
**Depends on:** T010, T011, T013, T014, T015
**Blocks:** Every operator-facing API ticket downstream
**Maps to:** `api-contracts.md` "Auth" section (POST /auth/setup, /auth/login, /auth/logout, GET /auth/me); `auth-and-security.md` "Login rate limiting".

---

## Objective

Implement the four auth endpoints that complete the first-run-through-login flow: `POST /api/v1/auth/setup` (first-time admin creation, available only when zero admin users exist), `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`. Login is rate-limited (10 attempts/min/IP via Redis sliding window). On successful login, the response sets both the session cookie and the CSRF cookie.

## Context

This ticket ties together all prior Phase 2 work: ORM models (T010), migrations (T011), password hashing (T013), session storage (T014), CSRF cookie issuance (T015). After this lands, every subsequent endpoint can rely on `get_current_admin_user` for auth.

## Read for context

- [`../03-technical/api-contracts.md`](../03-technical/api-contracts.md) — full Auth section (request/response shapes)
- [`../03-technical/auth-and-security.md`](../03-technical/auth-and-security.md) — "Login rate limiting" and "First-run setup"
- [`T013-password-hashing-pwdlib.md`](T013-password-hashing-pwdlib.md), [`T014-redis-sessions-auth-dependency.md`](T014-redis-sessions-auth-dependency.md), [`T015-csrf-middleware.md`](T015-csrf-middleware.md) — direct dependencies

## Files to create

- `backend/src/krelix/api/__init__.py` — empty
- `backend/src/krelix/api/v1/__init__.py` — empty
- `backend/src/krelix/api/v1/router.py` — `api_v1` APIRouter aggregating sub-routers
- `backend/src/krelix/api/v1/auth.py` — the auth router with the four endpoints
- `backend/src/krelix/api/v1/schemas/__init__.py` — empty (sub-package for Pydantic request/response schemas)
- `backend/src/krelix/api/v1/schemas/auth.py` — `SetupRequest`, `LoginRequest`, `UserResponse`
- `backend/src/krelix/api/v1/errors.py` — shared error-response shape helper
- `backend/src/krelix/auth/rate_limit.py` — Redis sliding-window rate-limit helper
- `backend/tests/test_auth_api.py` — integration tests covering all four endpoints + rate limit
- `backend/tests/test_rate_limit.py` — unit tests for the rate limiter

## Files to modify

- `backend/src/krelix/main.py` — `include_router(api_v1)`
- `backend/src/krelix/auth/csrf.py` — no changes (login/setup already exempt)

## Files to NOT touch

- ORM models — finalized in T010
- Migrations — finalized in T011

## Steps

1. **Write `backend/src/krelix/api/v1/schemas/auth.py`:**
   ```python
   from pydantic import BaseModel, Field

   class SetupRequest(BaseModel):
       username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
       password: str = Field(min_length=8, max_length=256)

   class LoginRequest(BaseModel):
       username: str
       password: str

   class UserResponse(BaseModel):
       id: str
       username: str
   ```

2. **Write `backend/src/krelix/auth/rate_limit.py`:**
   ```python
   import time
   from redis.asyncio import Redis

   async def check_and_increment(
       redis: Redis, *, key: str, window_seconds: int, max_attempts: int
   ) -> tuple[bool, int]:
       """
       Sliding-window rate-limit counter. Returns (allowed, current_count).
       Uses ZSET of timestamps; entries older than the window are trimmed.
       """
       now = time.time()
       cutoff = now - window_seconds
       async with redis.pipeline(transaction=True) as pipe:
           pipe.zremrangebyscore(key, 0, cutoff)
           pipe.zadd(key, {str(now): now})
           pipe.zcard(key)
           pipe.expire(key, window_seconds)
           _, _, count, _ = await pipe.execute()
       return count <= max_attempts, count
   ```

3. **Write `backend/src/krelix/api/v1/errors.py`** with a small helper:
   ```python
   def error_response(code: str, message: str, **details) -> dict:
       """Conventional error body shape from api-contracts.md."""
       payload = {"error": {"code": code, "message": message}}
       if details:
           payload["error"]["details"] = details
       return payload
   ```

4. **Write `backend/src/krelix/api/v1/auth.py`** with all four endpoints. Key behaviors:

   **`POST /api/v1/auth/setup`:**
   - Read DB: count admin users. If > 0, return 409 `{"error": {"code": "setup_already_complete", ...}}`.
   - Validate request via `SetupRequest`.
   - Hash password via `hash_password`.
   - Insert `AdminUser` row.
   - Create a session for this user via `SessionStore.create`.
   - Set session cookie + CSRF cookie on the response.
   - Return 201 with `UserResponse`.

   **`POST /api/v1/auth/login`:**
   - Extract client IP (from `request.client.host`, considering `X-Forwarded-For` if behind a trusted proxy — defer the trusted-proxy config to a Setting field if needed; for v1, use `request.client.host` directly).
   - Rate-limit key: `"krelix:rate_limit:login:" + client_ip`. Check via `check_and_increment(window=60s, max=10)`. If exceeded, return 429.
   - Look up user by username.
   - If not found: still call `verify_password` against a dummy hash to keep timing constant (or skip if not worried about timing oracles — acceptable for v1). Return 401 `invalid_credentials`.
   - If found: `verify_password(plaintext, user.password_hash)`. If invalid: return 401.
   - If valid + `new_hash` returned: update `user.password_hash`, commit.
   - Update `user.last_login_at = now()`.
   - Create session, set cookies, return 200 `UserResponse`.

   **`POST /api/v1/auth/logout`:**
   - Read session cookie. If present, `SessionStore.revoke`.
   - Clear session cookie. Do NOT clear CSRF cookie — frontend may want to issue a fresh one on next login; clearing it would also work, but leaving it is simpler and the cookie is meaningless without a session.
   - Return 204.

   **`GET /api/v1/auth/me`:**
   - Use `get_current_admin_user` dependency (raises 401 if not authenticated).
   - Return `UserResponse`.

5. **Wire `api_v1` router** in `backend/src/krelix/api/v1/router.py`:
   ```python
   from fastapi import APIRouter
   from .auth import router as auth_router

   api_v1 = APIRouter(prefix="/api/v1")
   api_v1.include_router(auth_router, prefix="/auth", tags=["auth"])
   ```

   And include it in `main.py` `create_app()`:
   ```python
   from .api.v1.router import api_v1
   app.include_router(api_v1)
   ```

6. **Write `backend/tests/test_auth_api.py`** (integration; requires DB + Redis):
   - `/setup` succeeds on a clean DB; second call → 409.
   - `/setup` validates username regex and password length.
   - `/login` with correct credentials returns 200 + sets `krelix_session` and `krelix_csrf` cookies.
   - `/login` with wrong password → 401 `invalid_credentials`.
   - `/login` with non-existent user → 401 `invalid_credentials` (no enumeration).
   - `/login` rate limit: 11th call within 60s → 429.
   - `/logout` clears session cookie and revokes Redis entry.
   - `/me` returns the user when authenticated; 401 when not.
   - CSRF: `/logout` requires CSRF cookie + header to be present and match.

7. **Write `backend/tests/test_rate_limit.py`** (integration; requires Redis):
   - First N calls allowed; (N+1)th denied.
   - After window expires, counter resets.

8. **Verify end-to-end:**
   - Start dev stack; `curl -X POST http://localhost:8000/api/v1/auth/setup -d '{"username":"admin","password":"correcthorse"}' -H 'Content-Type: application/json'` succeeds.
   - Second call returns 409.
   - `curl -X POST .../auth/login -d '...'` returns 200 with `Set-Cookie` headers.
   - `curl --cookie '<sid>' .../auth/me` returns the user.
   - `make test` integration green.

## Acceptance Criteria

- [ ] `POST /api/v1/auth/setup` works exactly once per DB; returns 201 + sets session+CSRF cookies; subsequent calls return 409.
- [ ] `POST /api/v1/auth/login` returns 200 on valid creds with both cookies set; 401 on invalid; 429 after 10/min/IP.
- [ ] `POST /api/v1/auth/logout` revokes the session in Redis and clears the cookie; returns 204; **requires CSRF** (because it's a mutating verb not on the exempt list).
- [ ] `GET /api/v1/auth/me` returns the authenticated user; 401 otherwise.
- [ ] Username validation enforces 3–64 chars and the `[a-zA-Z0-9_.-]+` regex.
- [ ] Password validation enforces 8–256 chars.
- [ ] Password hashing uses Argon2id via `hash_password` from T013.
- [ ] On successful login, if `verify_password` returns a non-None `new_hash`, it's persisted before the response.
- [ ] Login does not enumerate usernames: invalid-user and wrong-password both return the same 401 body.
- [ ] Rate limit uses Redis sliding window with key `krelix:rate_limit:login:<ip>`, window 60s, max 10.
- [ ] Error response bodies match the shape from `api-contracts.md` Conventions section.
- [ ] All four endpoints have integration tests covering the happy path AND error paths.
- [ ] `uv run mypy src/krelix/api` clean.
- [ ] `uv run pytest` (integration enabled) green.

## Out of Scope (for this ticket)

- Password change endpoint — implied need, but punt to a small ticket later (and add to backlog).
- Multi-factor auth — not in v1.
- Account lockout after N failed attempts — rate limit is the v1 control.
- Forgotten password flow — there is none in v1 (single operator; if locked out, the operator can `psql` in to reset).
- Audit logging of auth events — implied need but not in v1's Must list.
- Frontend wiring — Phase 11.

## Notes

- The login route is in the CSRF exempt list (T015) — the operator has no CSRF cookie until they log in. Once `set_csrf_cookie` runs as part of the login response, the operator has both cookies and CSRF protection kicks in for subsequent mutating requests.
- `setup` is similarly CSRF-exempt for the same reason. The "only works when zero admins exist" check is a form of one-time gate that compensates for the lack of CSRF.
- `logout` is **not** exempt — by the time the operator is logged in, they have a CSRF cookie. This is fine.
- Do not return any user fields beyond `id` and `username` in `UserResponse`. The `password_hash` field should never reach an API response — make sure your Pydantic schema doesn't accidentally serialize the SQLAlchemy model directly.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
