# T013 — Password hashing with pwdlib (Argon2id)

**Status:** Not started
**Phase:** 2 — Database foundation + auth
**Estimated session length:** 1 hr
**Depends on:** T002
**Blocks:** T016
**Maps to:** `auth-and-security.md` "Password hashing" — `pwdlib` with Argon2id, default Argon2 parameters tunable via env var.

---

## Objective

Provide a small, well-tested password-hashing module using `pwdlib`'s Argon2id backend. Hash on registration / password change; verify + transparently rehash on stale-algorithm matches. Expose two functions: `hash_password(plaintext)` and `verify_password(plaintext, stored_hash)`.

## Context

`passlib` is dead-end (last release 2020; broken on Python 3.13). `pwdlib` is the modern Python replacement, used by FastAPI Users and others. We use Argon2id (memory-hard, modern best practice). Parameters: `pwdlib`'s `argon2-cffi`-backed defaults (memory cost 64 MB, time cost 3, parallelism 4) are fine for v1; tunable via env var if the operator wants harder hashing.

## Read for context

- [`../03-technical/auth-and-security.md`](../03-technical/auth-and-security.md) — "Password hashing" section
- [`../03-technical/dependencies-and-risks.md`](../03-technical/dependencies-and-risks.md) — pwdlib row

## Files to create

- `backend/src/krelix/passwords.py` — the module
- `backend/tests/test_passwords.py` — unit tests

## Files to modify

- None

## Files to NOT touch

- Anything else; focused utility module.

## Steps

1. **Write `backend/src/krelix/passwords.py`:**
   ```python
   from pwdlib import PasswordHash
   from pwdlib.hashers.argon2 import Argon2Hasher

   _password_hash = PasswordHash((Argon2Hasher(),))

   def hash_password(plaintext: str) -> str:
       """Hash a password using Argon2id. Returns the encoded hash string."""
       if not plaintext:
           raise ValueError("password must be non-empty")
       return _password_hash.hash(plaintext)

   def verify_password(plaintext: str, stored_hash: str) -> tuple[bool, str | None]:
       """
       Verify `plaintext` against `stored_hash`.

       Returns:
           (is_valid, updated_hash). If `is_valid` is True and `updated_hash` is not None,
           the caller should persist the updated hash (transparent algorithm/parameter upgrade).
       """
       valid, new_hash = _password_hash.verify_and_update(plaintext, stored_hash)
       return valid, new_hash
   ```

2. **Write `backend/tests/test_passwords.py`:**
   - `hash_password("hunter2")` returns a string starting with `$argon2id$`.
   - `verify_password("hunter2", hash)` returns `(True, None)` for a fresh hash.
   - `verify_password("wrong", hash)` returns `(False, None)`.
   - `hash_password("")` raises `ValueError`.
   - Two calls to `hash_password("same")` yield different hashes (salt randomness).
   - **Bcrypt → Argon2id auto-upgrade:** Given a bcrypt hash (created with `passlib` or directly with `bcrypt` for the test only), `verify_password(plaintext, bcrypt_hash)` returns `(True, new_argon2_hash)` — the second tuple element is non-None, indicating the caller should rotate.
     - Note: only do this if `pwdlib`'s `PasswordHash` is configured to also accept bcrypt for backward compat. For v1, since we start fresh with Argon2id, this is **optional** — if it adds friction, skip and document.

3. **Verify:**
   - `uv run pytest tests/test_passwords.py` green.
   - `uv run mypy src/krelix/passwords.py` clean.

## Acceptance Criteria

- [ ] `backend/src/krelix/passwords.py` exposes `hash_password` and `verify_password`.
- [ ] `hash_password` produces Argon2id-encoded hashes.
- [ ] `verify_password` returns `(bool, str | None)` — `None` for fresh hashes, a new hash string for stale-algorithm matches.
- [ ] Empty password input is rejected.
- [ ] Same input produces different hashes (salt randomness).
- [ ] `uv run pytest tests/test_passwords.py` green.
- [ ] `uv run mypy` clean.

## Out of Scope (for this ticket)

- Storing passwords — that's T016 (auth API).
- Argon2 parameter tuning via env var — punt to a future operator runbook concern; the `pwdlib` defaults are fine for v1.
- Password complexity policy enforcement (length / character requirements) — T016 can add that on the API layer.
- Bcrypt fallback — optional; skip if `pwdlib` makes it awkward.

## Notes

- The `pwdlib[argon2]` package install pulls `argon2-cffi` automatically. Verify both are in `uv.lock`.
- `_password_hash` is a module-level singleton — initializing it costs nothing and avoids repeated setup. Don't refactor to a per-call instance.
- Resist exposing `PasswordHash` directly to callers; keep the surface to two functions.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
