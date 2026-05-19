# Auth and Security — Krelix

v1 is **LAN-only, single-operator OSS**. The security posture matches: minimal but disciplined. Two distinct trust planes — the operator's session and the agent's protocol — each with its own auth. The bigger enterprise auth stack (Keycloak + OPA + Vault + SPIFFE recommended by the market research PDF) is intentionally **deferred to the eventual commercial product**.

## Authentication

### Operator surface

**Approach:** Session cookie after username + password login. Backed by Redis for session state (lets us revoke sessions on logout / token-rotate; we already run Redis for the job queue).

**Implementation details:**

- **Password hashing:** `pwdlib` (MIT) with **Argon2id** as the primary algorithm (via `argon2-cffi`). `passlib` is **not used** — its last release was 2020 and it does not work on Python 3.13+; `pwdlib` is the modern replacement (used by FastAPI Users and others) and ships sane Argon2 defaults plus `verify_and_update` for transparent algorithm upgrades. Default Argon2 parameters: the `argon2-cffi` library defaults (memory cost 64 MB, time cost 3, parallelism 4) are acceptable; tunable via env var if the operator wants harder hashing.
- **Session cookie:**
  - Name: `krelix_session`
  - `HttpOnly`, `SameSite=Lax`, `Secure` when the deployment is behind TLS (env-flag controlled).
  - Cookie value is an opaque random ID (256 bits, base64url); session data lives in Redis under key `krelix:session:<id>`.
  - Lifetime: 30 days idle, 14-day rolling refresh.
- **CSRF protection (double-submit pattern):**
  - Issued on login: a non-HttpOnly cookie `krelix_csrf` with a random token, AND every mutating request (`POST/PUT/PATCH/DELETE`) must echo it in the `X-CSRF-Token` header.
  - Pure-read GET endpoints are exempt.
- **Login rate limiting:** 10 attempts / minute / IP, enforced in Redis with a sliding window counter. Soft lockout (HTTP 429) — never permanent.
- **First-run setup:** When zero `admin_user` rows exist, all routes except `/api/v1/auth/setup` return `401 setup_required`. The UI redirects to a one-time setup page that calls `POST /api/v1/auth/setup` to create the first admin.
- **Library defaults:** Starlette's `SessionMiddleware` is NOT used directly (it signs cookies but doesn't centralize storage). Sessions are managed in a small custom dependency that reads/writes Redis.

### Agent surface

**Approach:** Bearer token per registered host agent. Each `endpoint` has exactly one active `agent_registration_token`.

**Implementation details:**

- **Token format:** `krelix_agt_<32 bytes of url-safe base64>` (≈ 43 character random suffix).
- **Storage:** Only the SHA-256 hash of the token is stored in `agent_registration_token.token_hash`. The bearer plaintext is returned exactly once at registration time (UI + API response). If the operator loses it, they must `POST /api/v1/endpoints/{id}/regenerate-token` to get a fresh one (revokes the previous).
- **Wire format:** `Authorization: Bearer krelix_agt_...` on the initial `POST /agent/v1/register` call AND on the WebSocket connection's initial HTTP upgrade request.
- **Lifecycle:**
  - **Bootstrap (consumed_at = NULL):** Token can be used to register an agent; the registration call marks `consumed_at = now()`.
  - **Operational (consumed_at IS NOT NULL):** Same token continues to authenticate the agent's ongoing WebSocket and config-pull operations.
  - **Revoked (revoked_at IS NOT NULL):** Authentication fails. Set when the operator regenerates the token or unregisters the endpoint.
- **Rotation:** Operator-initiated only in v1 (via `POST /api/v1/endpoints/{id}/regenerate-token`). Automatic rotation is a v1.x/v2 concern.

## Authorization

**Roles / permissions:** v1 has a single role — **`admin`** — held implicitly by the only `admin_user` row. There is no RBAC machinery in v1 because there is only one role.

**Implementation hint for forward compatibility:** Route handlers should depend on a `current_admin_user` resolver dependency that returns the authenticated `admin_user`. When the commercial product later introduces RBAC, the dependency expands to a `current_user_with_permissions(...)` form. **Do not** add a permissions table or `@requires_role()` decorator machinery in v1 — that's premature.

**Agent endpoints:** The bearer-token check at the surface layer is sufficient — there is one principal per agent token, namely "the agent of this endpoint." Authorization is implicit: an agent can only act on its own endpoint's resources. Cross-endpoint authority is a code-level invariant, not an RBAC check.

## Secrets Management

**Single root secret:** Environment variable `KRELIX_SECRET_KEY` — at least 32 random bytes, base64-encoded — is the root of all symmetric crypto in v1. It is provided to the control plane container (via env var or Docker Compose `env_file`) and must persist across restarts.

**Derived purposes (each via HKDF with a distinct `info` label):**

- `krelix:session-signing` — HMAC for any signed-cookie use (defense in depth; primary session storage is Redis with random IDs).
- `krelix:hf-token-encryption` — AES-256-GCM key for encrypting the operator's HuggingFace token at rest in `huggingface_credential.token_encrypted`. IV is per-record (12 random bytes); ciphertext = IV ‖ AES-GCM(plaintext) ‖ auth_tag.

**What counts as a secret (full inventory):**

| Secret | Storage | At rest | In transit |
|--------|---------|---------|------------|
| `KRELIX_SECRET_KEY` | Env var on control plane | Operator-managed (Docker Compose `.env`, systemd unit env) | N/A — never leaves the control-plane host |
| Admin password | `admin_user.password_hash` | Argon2id hash (via `pwdlib`) | TLS-recommended; HTTPS-or-LAN-trust acceptable in v1 |
| Admin session ID | `krelix_session` cookie | Random 256-bit ID; data in Redis under `krelix:session:<id>` | HttpOnly cookie |
| CSRF token | `krelix_csrf` cookie | Random per-session | Non-HttpOnly cookie + header echo |
| HF token | `huggingface_credential.token_encrypted` | AES-256-GCM (key derived from `KRELIX_SECRET_KEY`) | TLS (HF Hub is HTTPS); never logged |
| Agent bearer tokens | `agent_registration_token.token_hash` | SHA-256 hash (one-way) | TLS-recommended on agent ↔ control plane channel |
| Redis password | Env var; Redis `requirepass` | Plain in compose env | LAN-internal; localhost-only Redis listener preferred |
| Postgres password | Env var | Plain in compose env | LAN-internal |

**Rotation:**

- `KRELIX_SECRET_KEY`: rotation requires re-encrypting `huggingface_credential.token_encrypted` (one row) and invalidating all sessions. Documented runbook task; not automated in v1. Operator-initiated.
- Admin password: changeable via `POST /api/v1/auth/change-password` (deferred to a Should story implicitly — add to backlog if not already present).
- HF token: replaceable any time via `PUT /api/v1/settings/huggingface`.
- Agent tokens: operator-initiated regeneration.

**Critical operator note:** If `KRELIX_SECRET_KEY` is lost, the HF token cannot be recovered (will need re-entry). Document this in deployment runbook. Sessions become invalid but the operator can simply log in again.

## Sensitive Data

v1 handles three classes of sensitive data:

1. **Operator credentials and session material** — bcrypt + opaque Redis-backed session IDs. Never logged, never returned in responses.
2. **HuggingFace token** — AES-256-GCM at rest, TLS in transit (to HF Hub), never logged. Outbound HTTPS requests to HF use the token in `Authorization: Bearer ...` headers; structlog redaction filter strips `Authorization` from request logs.
3. **Model artifact licenses and gating metadata** — captured at intake (US-S-02). Surfaced in UI; not sensitive per se, but **the operator must keep their HF token compliant** with the access terms of any gated model they download. Krelix surfaces declared license info but does not enforce license terms.

No PII, no financial data, no regulated data is in scope for v1.

## Trust Boundaries

The architecture document defines the system-level trust boundaries; this section adds security-specific posture:

- **Inference engine code is treated as third-party and untrusted to behave well, but trusted enough to run with GPU access.** This applies whether the engine runs as a container or as a subprocess:
  - **Container mode:** Agent does NOT pass `--privileged`. GPU access via the NVIDIA Container Toolkit (`--gpus 'device=<idx>'`) with specific devices only, no general `/dev` exposure. Containers run with the image's default non-root user where supported.
  - **Bare-metal/systemd mode:** Agent and engine subprocesses run as a dedicated unprivileged `krelix-agent` system user (no login shell), added to the `video` or `render` group for GPU access. Systemd unit hardening on `krelix-agent.service`: `NoNewPrivileges=yes`, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`, `ReadWritePaths=<hot-tier> <vault-mount>`, `CapabilityBoundingSet=` (empty — no capabilities). Engine subprocesses inherit this hardened environment.
- **`--trust-remote-code` is OFF by default.** Some HF models require it to load custom modeling code shipped in the repo. v1 stance: **never pass `--trust-remote-code` to vLLM**. If a model genuinely requires it, deployment will fail; the operator gets a clear error explaining the trust_remote_code requirement and is offered an explicit opt-in checkbox at deploy time (deferred to implementation — add to backlog as US-S or US-C). Opt-in deployments are flagged in the `deployment` row for audit.
- **Model conversion scripts are NOT executed in v1.** Krelix downloads what HF provides; if vLLM cannot load it directly, deployment fails. Conversion (`convert_hf_to_gguf.py`, BitsAndBytes quantization, LLM Compressor) is explicitly out of v1 scope.
- **Operator UI rendering of HF model card content:** HuggingFace model cards can contain user-supplied Markdown/HTML. Krelix renders model card summaries via React's safe escaping (no `dangerouslySetInnerHTML`) and runs untrusted Markdown through a sanitizer (`rehype-sanitize` or `DOMPurify`) before display.

## Threat Model

Coverage targets the OWASP-top-10-relevant subset for an LAN-only single-operator tool.

| Threat | Likelihood | Impact | Mitigation |
|--------|-----------|--------|------------|
| Brute-force admin login | low (LAN-only) | high | Argon2id (memory-hard) via `pwdlib` + 10-attempt/min/IP rate limit |
| Session hijack via stolen cookie | low (LAN, HttpOnly) | high | HttpOnly + SameSite=Lax + Secure-when-TLS; opaque random IDs; logout revokes Redis entry |
| CSRF from malicious LAN page | medium | medium | Double-submit CSRF token; SameSite=Lax cookie further reduces |
| XSS via HF model card content rendered in UI | medium | medium | React default escaping + Markdown sanitizer; no `dangerouslySetInnerHTML` |
| SQL injection | low | high | SQLAlchemy 2.x parameterized queries everywhere; no string-concatenated SQL |
| Stolen HF token | low | medium | AES-256-GCM at rest, never logged, never returned in responses |
| Stolen agent bearer token | low (LAN) | high | One-time bootstrap (`consumed_at`); operator can regenerate; SHA-256 hash storage |
| MITM on agent ↔ control plane (LAN sniff) | low | high | TLS strongly recommended for v1 deployments where the LAN isn't fully trusted; operator can put a reverse proxy in front (their nginx-proxy-manager, Caddy, etc.) |
| MITM on operator UI traffic | low | high | Same — TLS via operator-managed reverse proxy is supported and recommended |
| Engine container escape (container mode) | low (well-known image) | high | No `--privileged`; specific `--gpus device=...`; network namespace; no host volume mounts beyond the hot-tier read mount; vLLM upstream image only |
| Engine process compromise (bare-metal mode) | low | high | Runs as unprivileged `krelix-agent` user via systemd; hardened unit (NoNewPrivileges, ProtectSystem=strict, empty CapabilityBoundingSet); engine inherits the same constraints |
| Untrusted model code (`trust_remote_code`) | medium | high | OFF by default; explicit per-deployment opt-in only; flagged in audit |
| Path traversal / file write via HF model name | low | medium | All HF model refs validated against a strict regex (`[a-zA-Z0-9._/-]{1,200}`) before being used in filesystem operations; `huggingface_hub`'s cache layout already isolates by repo namespace |
| Dependency vulnerabilities (Python or JS) | medium | medium | `uv pip audit` and `pnpm audit` run in CI; lockfiles committed; quarterly review cadence documented |
| Secrets in logs | medium | high | structlog `processors` redact common secret fields (`authorization`, `token`, `password`, `hf_token`, `secret_key`) by name; never log full request/response bodies for auth/settings endpoints |
| Redis exposed to LAN | low | high | Redis listener bound to `127.0.0.1` (Docker network in compose); `requirepass` set; never exposed externally |
| Postgres exposed to LAN | low | high | Same — bound to compose-internal network |
| Denial of service via repeated deploys | low (single operator) | medium | Bounded retry budget on auto-iteration; max-deployments-per-endpoint check at API layer (deferred to implementation) |
| Stale or revoked agent token continuing to act | low | medium | Every WebSocket frame's auth is checked at connect time; revoked tokens fail reconnect; long-lived connections re-validated periodically (cadence deferred) |

## TLS Strategy for v1

v1 is shipped HTTP-by-default with a clearly documented "put a reverse proxy in front of it" path:

- Krelix control plane container exposes plain HTTP on port 8000 inside the compose network.
- **If operator wants TLS:** documented runbook recipe to put their existing reverse proxy (nginx-proxy-manager in their case, or Caddy, Traefik, etc.) in front, terminating TLS and forwarding to Krelix. Krelix sets the `Secure` flag on cookies automatically when it sees `X-Forwarded-Proto: https`.
- **Agent ↔ control plane:** The agent's `stream_url` (returned at registration) is whatever URL the operator specified. If the operator put TLS in front, agents connect via `wss://`. If not, `ws://` on the LAN.

Krelix does **not** ship a built-in TLS terminator or Let's Encrypt integration in v1. Reverse-proxy delegation matches the operator's existing infrastructure pattern (they already run nginx-proxy-manager) and avoids reinventing well-solved infrastructure.

## Compliance / Legal Notes

- **HuggingFace gated models:** access governed by the operator's HF token; Krelix passes the token through `huggingface_hub` and respects gating failures. **The operator is responsible for accepting any per-model license/access terms on HuggingFace before Krelix can download.**
- **Model licenses:** captured at intake into `model.declared_license`; surfaced in UI at search and deployment time (US-S-02). Krelix uses **warn-and-proceed** in v1 — missing/unresolved license metadata shows a clear warning indicator, but deployment is allowed. The commercial product is where this becomes enforced.
- **Commercial-license safety:** every library named in [`stack.md`](stack.md) is MIT / BSD / Apache 2.0 / PostgreSQL License. No AGPL, no GPL. The license audit is in `stack.md`'s "Key Libraries" table.
- **No data residency / sovereignty concerns** in scope for v1 (single-operator homelab).

## Logging and Audit

- All HTTP requests are logged via structlog with: request id, method, path, status, latency, authenticated user id. Bodies for auth/settings endpoints are NEVER logged.
- All mutating operations on `endpoint`, `vault`, `deployment`, and `settings` write a `deployment_event` row or equivalent audit trail entry (depending on what they mutate). Operator-facing UI surfaces this as a "Recent activity" view (deferred to UI implementation).
- Agent-to-control-plane frames are NOT logged at info level (volume is too high) — only at debug. Specific frame types (deployment failures, eviction events) are persisted as `deployment_event` rows.
