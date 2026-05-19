# T015 — CSRF middleware (double-submit)

**Status:** Not started
**Phase:** 2 — Database foundation + auth
**Estimated session length:** 1.5 hr
**Depends on:** T009
**Blocks:** T016
**Maps to:** `auth-and-security.md` "CSRF protection (double-submit pattern)"; `api-contracts.md` "Authentication" conventions.

---

## Objective

Add a CSRF protection middleware to the FastAPI app using the double-submit pattern. A random CSRF token is issued at login (or on first GET if no session yet — TBD per behavior choice below) as a non-HttpOnly cookie `krelix_csrf`. Every mutating request (POST/PUT/PATCH/DELETE) must echo the cookie value in an `X-CSRF-Token` header; mismatched or missing pairs return 403.

## Context

`SameSite=Lax` on the session cookie already eliminates most CSRF surface, but it's not sufficient against same-origin attacks (a compromised page on the same host could still drive the API). The double-submit pattern adds a per-session random token that JavaScript on the legitimate frontend can read (it's non-HttpOnly) and echo, but a cross-origin attacker can't read. This is straightforward, requires no server-side per-request state, and fits the v1 single-operator deployment.

## Read for context

- [`../03-technical/auth-and-security.md`](../03-technical/auth-and-security.md) — "CSRF protection (double-submit pattern)" subsection
- [`../03-technical/api-contracts.md`](../03-technical/api-contracts.md) — "Authentication" / mutating-verb expectations
- [`T014-redis-sessions-auth-dependency.md`](T014-redis-sessions-auth-dependency.md) — sets the session cookie; CSRF cookie is its companion

## Files to create

- `backend/src/krelix/auth/csrf.py` — middleware + helpers
- `backend/tests/test_csrf.py` — tests

## Files to modify

- `backend/src/krelix/main.py` — register the CSRF middleware in `create_app()` (after the lifespan setup, before route inclusion)

## Files to NOT touch

- Auth API routes (T016) — they will *use* the CSRF cookie helpers from this ticket, but the routes themselves are T016.
- Session storage (T014) — finalized.

## Steps

1. **Write `backend/src/krelix/auth/csrf.py`:**
   ```python
   import secrets
   from fastapi import Request, Response, status
   from fastapi.responses import JSONResponse
   from starlette.middleware.base import BaseHTTPMiddleware

   COOKIE_CSRF = "krelix_csrf"
   HEADER_CSRF = "X-CSRF-Token"
   SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
   EXEMPT_PATHS = (
       "/healthz",
       "/readyz",
       "/agent/",  # agent surface uses bearer-token auth, no CSRF
       "/api/v1/auth/login",  # see below
       "/api/v1/auth/setup",  # see below
   )

   def issue_csrf_token() -> str:
       return secrets.token_urlsafe(32)

   def set_csrf_cookie(response: Response, token: str, *, secure: bool) -> None:
       response.set_cookie(
           key=COOKIE_CSRF,
           value=token,
           httponly=False,   # JS needs to read it
           samesite="lax",
           secure=secure,
           max_age=30 * 24 * 60 * 60,
           path="/",
       )

   class CSRFMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request: Request, call_next):
           if request.method in SAFE_METHODS:
               return await call_next(request)
           if any(request.url.path.startswith(p) for p in EXEMPT_PATHS):
               return await call_next(request)

           cookie = request.cookies.get(COOKIE_CSRF)
           header = request.headers.get(HEADER_CSRF)
           if not cookie or not header or not secrets.compare_digest(cookie, header):
               return JSONResponse(
                   status_code=status.HTTP_403_FORBIDDEN,
                   content={"error": {"code": "csrf_invalid",
                                       "message": "CSRF token missing or mismatched."}},
               )
           return await call_next(request)
   ```

   **Decision: login and setup are CSRF-exempt** because the operator hasn't yet received a CSRF cookie. They're protected by other means (rate limiting on login; one-time setup gate on setup). Logout is **not** exempt — by the time the operator logs out, they have a CSRF cookie.

2. **Wire the middleware** in `main.py`:
   ```python
   from .auth.csrf import CSRFMiddleware

   def create_app() -> FastAPI:
       app = FastAPI(..., lifespan=lifespan)
       app.add_middleware(CSRFMiddleware)
       # ... routes
       return app
   ```

3. **Write `backend/tests/test_csrf.py`:**
   - `GET /healthz` — no CSRF required, 200.
   - `POST /api/v1/some-protected-endpoint` (will be a real endpoint after T016; for now, create a tiny test-only endpoint inside the test fixture) — missing cookie → 403 `csrf_invalid`.
   - Same, with mismatched cookie + header → 403 `csrf_invalid`.
   - Same, with matching cookie + header → call passes through (200, or the underlying route's response).
   - `POST /api/v1/auth/login` exempt — 401 or similar from the login route, not 403 from CSRF.
   - `POST /agent/v1/register` exempt — `/agent/` paths skip CSRF entirely.
   - `compare_digest` is used (constant-time) — verified by reading source, not behavior.

4. **Verify:**
   - `uv run pytest tests/test_csrf.py` green.
   - `uv run mypy` clean.
   - Smoke: spin up the app, `curl -X POST http://localhost:8000/api/v1/somewhere` with no cookie returns 403 with the right JSON shape.

## Acceptance Criteria

- [ ] `backend/src/krelix/auth/csrf.py` exposes `CSRFMiddleware`, `issue_csrf_token`, `set_csrf_cookie`, and the `COOKIE_CSRF`/`HEADER_CSRF` constants.
- [ ] Middleware is registered in `main.py`'s `create_app()`.
- [ ] Safe methods (GET, HEAD, OPTIONS) pass through unmodified.
- [ ] Exempt paths (`/healthz`, `/readyz`, `/agent/...`, `/api/v1/auth/login`, `/api/v1/auth/setup`) pass through.
- [ ] Mutating requests on non-exempt paths require matching `krelix_csrf` cookie and `X-CSRF-Token` header; mismatch → 403 with `{"error": {"code": "csrf_invalid", ...}}`.
- [ ] Token comparison uses `secrets.compare_digest` (constant-time).
- [ ] CSRF cookie is non-HttpOnly, SameSite=Lax, Secure-when-HTTPS, path `/`, 30-day TTL — set via `set_csrf_cookie`.
- [ ] Tests green; mypy clean.

## Out of Scope (for this ticket)

- Issuing the CSRF cookie on login — T016 calls `set_csrf_cookie` from its login route.
- Frontend integration — handled when the frontend grows real auth UI (Phase 11-ish).
- Refresh / rotation of CSRF token mid-session — not needed in v1; the token lives as long as the session.
- Per-form / per-request unique tokens — overkill for v1; the per-session token is enough for double-submit.

## Notes

- Resist over-engineering: the per-session token is fine. Don't add request-binding (token tied to URL or timestamp); it adds complexity for negligible v1 benefit.
- Don't put the CSRF middleware behind the session middleware ordering-wise — they're independent. Middleware order in FastAPI is "added last runs outermost," so `app.add_middleware(CSRFMiddleware)` after `app.add_middleware(SessionMiddleware)` (if there were one) would mean CSRF runs first on the way in. We don't have a separate session middleware (we use a dependency), so just add CSRF normally.
- The exempt-path list is small. If a future ticket needs to exempt another path, surface the request — exemptions should be rare.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
