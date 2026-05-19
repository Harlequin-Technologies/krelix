# T027 — Agent core: config loading + structlog + CLI scaffold

**Status:** Not started
**Phase:** 5 — Host agent skeleton (container mode)
**Estimated session length:** 1.5 hr
**Depends on:** T004
**Blocks:** T028, T029
**Maps to:** `architecture.md` Component 5; `deployment.md` agent env vars; `auth-and-security.md` structlog redaction.

---

## Objective

Set up the agent's runtime config (pydantic-settings reading env vars), structlog with the same redaction filter as the backend, and a `typer`-based CLI with `run`, `register`, and `version` subcommands. `run` is the main daemon entrypoint (wired in T028+); for this ticket it prints "running" and idles. No registration or GPU code yet.

## Read for context

- [`../03-technical/architecture.md`](../03-technical/architecture.md) — Component 5
- [`../03-technical/deployment.md`](../03-technical/deployment.md) — agent env vars (`KRELIX_CONTROL_URL`, `KRELIX_AGENT_TOKEN`, `KRELIX_AGENT_RUNTIME_MODE`, `KRELIX_HOT_TIER_PATH`, `KRELIX_VAULT_MOUNT_PATH`, `KRELIX_ENGINE_VLLM_PYTHON`, `KRELIX_ENGINE_VLLM_MODULE`)
- [`T005-control-plane-dockerfile-fastapi-skeleton.md`](T005-control-plane-dockerfile-fastapi-skeleton.md) — structlog pattern to mirror

## Files to create

- `agent/src/krelix_agent/config.py` — `Settings` class
- `agent/src/krelix_agent/logging.py` — structlog config with redaction (mirror backend)
- `agent/src/krelix_agent/cli.py` — refactor to add `run`, `register`, `version`
- `agent/tests/test_config.py`
- `agent/tests/test_logging_redaction.py`

## Files to modify

- `agent/pyproject.toml` — verify scripts entry still exposes `krelix-agent = "krelix_agent.cli:app"`

## Steps

1. Write `config.py` with fields: `control_url`, `agent_token`, `agent_runtime_mode` (Literal['docker','systemd']), `hot_tier_path`, `vault_mount_path` (Optional), `engine_vllm_python` (Optional, systemd-mode only), `engine_vllm_module` (Optional), `heartbeat_interval_seconds` (default 30).
2. Validation: in `systemd` mode, `engine_vllm_python` and `engine_vllm_module` are required (use a `model_validator`).
3. `logging.py` — duplicate the backend's redaction processor; agent-specific logger name `krelix.agent`.
4. `cli.py` — three commands: `version` (already exists from T004), `register` (placeholder; prints "TODO: register"), `run` (calls `configure_logging()` then sleeps in a loop, log "running").
5. Tests: config rejects missing required fields; systemd mode rejects missing engine paths; redaction filter replaces values for `authorization`, `agent_token`, `token`.

## Acceptance Criteria

- [ ] `KRELIX_CONTROL_URL` and `KRELIX_AGENT_TOKEN` are required; missing → clear error at startup.
- [ ] `KRELIX_AGENT_RUNTIME_MODE=systemd` without engine paths → validation error.
- [ ] `krelix-agent version`, `krelix-agent register`, `krelix-agent run` all callable.
- [ ] structlog redacts `agent_token` and `authorization` values.
- [ ] `mypy` clean, `pytest` green.

## Out of Scope

- Actual registration (T028), WebSocket (T029), GPU inventory (T028), deploy handling (T037)

## Notes

- Keep the agent's settings narrow. v1 doesn't need feature flags, debug toggles, etc.
- Heartbeat interval is configurable for testing flexibility but defaults to 30s.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
