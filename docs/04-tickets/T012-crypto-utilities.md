# T012 — Crypto utilities (HKDF + AES-256-GCM for HF token encryption)

**Status:** Not started
**Phase:** 2 — Database foundation + auth
**Estimated session length:** 1.5 hr
**Depends on:** T009
**Blocks:** Nothing in Phase 2 directly; downstream tickets that touch the HF token will import this module.
**Maps to:** `auth-and-security.md` "Secrets Management" — `KRELIX_SECRET_KEY` derives all symmetric crypto via HKDF; HF token encrypted with AES-256-GCM.

---

## Objective

Provide a small, well-tested crypto module that derives per-purpose keys from `KRELIX_SECRET_KEY` via HKDF, and encrypts/decrypts the HuggingFace token with AES-256-GCM. The module is intentionally tiny — one HKDF helper, one encrypt function, one decrypt function — and is the single place all symmetric crypto lives.

## Context

`auth-and-security.md` specifies: single root secret in env (`KRELIX_SECRET_KEY`), HKDF-derived per-purpose keys (`krelix:hf-token-encryption`, `krelix:session-signing`), AES-256-GCM for HF token storage with a per-record IV (12 random bytes), ciphertext format `IV ‖ AES-GCM(plaintext) ‖ auth_tag`. The `cryptography` library is already in deps (T002).

## Read for context

- [`../03-technical/auth-and-security.md`](../03-technical/auth-and-security.md) — "Secrets Management" section
- [`T009-settings-db-redis-connections.md`](T009-settings-db-redis-connections.md) — Settings exposes the secret as `SecretStr`

## Files to create

- `backend/src/krelix/crypto.py` — the module
- `backend/tests/test_crypto.py` — unit tests

## Files to modify

- None

## Files to NOT touch

- Anything else; this is a focused utility module.

## Steps

1. **Write `backend/src/krelix/crypto.py`:**
   ```python
   import os
   from cryptography.hazmat.primitives import hashes
   from cryptography.hazmat.primitives.ciphers.aead import AESGCM
   from cryptography.hazmat.primitives.kdf.hkdf import HKDF
   from .config import get_settings

   # Per-purpose HKDF info labels. ADD new labels here, never reuse.
   HKDF_INFO_HF_TOKEN = b"krelix:hf-token-encryption"
   HKDF_INFO_SESSION_SIGNING = b"krelix:session-signing"

   def _derive_key(info: bytes, length: int = 32) -> bytes:
       """Derive a per-purpose symmetric key from KRELIX_SECRET_KEY via HKDF-SHA256."""
       root = get_settings().secret_key.get_secret_value().encode()
       hkdf = HKDF(algorithm=hashes.SHA256(), length=length, salt=None, info=info)
       return hkdf.derive(root)

   def encrypt_hf_token(plaintext: str) -> bytes:
       """Encrypt the HF token. Returns IV (12 bytes) ‖ ciphertext ‖ auth_tag."""
       key = _derive_key(HKDF_INFO_HF_TOKEN)
       iv = os.urandom(12)
       aesgcm = AESGCM(key)
       ct_and_tag = aesgcm.encrypt(iv, plaintext.encode("utf-8"), associated_data=None)
       return iv + ct_and_tag

   def decrypt_hf_token(blob: bytes) -> str:
       """Decrypt the HF token from the IV‖ciphertext‖tag blob."""
       if len(blob) < 12 + 16:
           raise ValueError("ciphertext too short")
       iv, ct_and_tag = blob[:12], blob[12:]
       key = _derive_key(HKDF_INFO_HF_TOKEN)
       aesgcm = AESGCM(key)
       return aesgcm.decrypt(iv, ct_and_tag, associated_data=None).decode("utf-8")

   def get_session_signing_key() -> bytes:
       """Used by signed-cookie helpers / CSRF token signing."""
       return _derive_key(HKDF_INFO_SESSION_SIGNING)
   ```

2. **Write `backend/tests/test_crypto.py`:**
   - Round-trip: `decrypt_hf_token(encrypt_hf_token("hf_abc123"))` returns `"hf_abc123"`.
   - Different IVs: calling `encrypt_hf_token("same")` twice yields different ciphertext (proves IV randomness).
   - Tamper detection: flipping a bit in the ciphertext causes `decrypt_hf_token` to raise `InvalidTag` (or wrapped to a clean Krelix error).
   - Wrong key fails decrypt: monkeypatch `get_settings` to return a different secret; decrypt fails.
   - HKDF determinism: same secret + same info yields same derived key (verify by mocking and inspecting).
   - Length: ciphertext output is exactly `12 + len(plaintext_utf8) + 16` bytes.

3. **Verify:**
   - `uv run pytest tests/test_crypto.py` green.
   - `uv run mypy src/krelix/crypto.py` clean.

## Acceptance Criteria

- [ ] `backend/src/krelix/crypto.py` exposes `encrypt_hf_token`, `decrypt_hf_token`, `get_session_signing_key`, and `_derive_key`.
- [ ] HKDF derivation uses SHA-256 with a stable info label per purpose; labels are module-level constants.
- [ ] AES-256-GCM is used for the HF token; per-call IV is 12 random bytes; output format is exactly `IV ‖ ciphertext ‖ tag`.
- [ ] Round-trip tests pass.
- [ ] Tamper detection works (bit flip in ciphertext → decrypt raises).
- [ ] Different IVs per call (verified by encrypting the same plaintext twice).
- [ ] `uv run mypy` clean; `uv run pytest tests/test_crypto.py` green.

## Out of Scope (for this ticket)

- Storing or retrieving the HF token from the DB — that lands when the HF credential API is implemented (Phase 3)
- Session cookies / CSRF use of the signing key — `T014` and `T015` consume it
- Any kind of asymmetric crypto — not needed in v1
- Key rotation procedure — documented operator runbook only, no code

## Notes

- The `cryptography` library is already in the dep tree. Don't add `pynacl` or any other crypto lib.
- Resist adding "general crypto utilities" beyond what's in this ticket. If a new use case needs symmetric crypto later, add a new HKDF info label here — don't roll separate crypto modules elsewhere.
- The HKDF `salt=None` is intentional — HKDF with `salt=None` is HKDF-Extract-Skip, equivalent to using a zero-byte salt of the right length. We don't have a per-derivation salt because the root key is already cryptographically random.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
