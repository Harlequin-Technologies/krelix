# T054 — vLLM subprocess engine adapter (bare-metal mode)

**Status:** Not started
**Phase:** 12 — Bare-metal/systemd host agent path
**Estimated session length:** 3 hr
**Depends on:** T037, T044
**Blocks:** T055
**Maps to:** `architecture.md` "vLLM containers" / engine processes (subprocess form factor); `auth-and-security.md` bare-metal security posture.

---

## Objective

Implement `VllmSubprocessAdapter` (mirror of `VllmContainerAdapter` from T037) that launches vLLM as a local subprocess instead of a Docker container. Selected automatically when the agent's `KRELIX_AGENT_RUNTIME_MODE=systemd`. Captures stdout/stderr for the same log streaming pipeline.

## Files to create

- `agent/src/krelix_agent/engines/vllm_subprocess.py`
- `agent/tests/test_vllm_subprocess_adapter.py`

## Files to modify

- `agent/src/krelix_agent/commands/deploy.py` — select adapter based on `settings.agent_runtime_mode`
- `agent/src/krelix_agent/log_tail.py` — confirm `tail_process` works for the subprocess

## Steps

1. `VllmSubprocessAdapter`:
   - `start(deployment_id, model_path, gpu_indices, args) -> StartResult`:
     - Build command: `[settings.engine_vllm_python, "-m", settings.engine_vllm_module, "--model", str(model_path), ...]` with args translated from the same JSON config the container adapter consumes.
     - Pick a free port (use `socket` to find one); set `--port`.
     - Set `CUDA_VISIBLE_DEVICES` env var from `gpu_indices`.
     - Spawn via `asyncio.create_subprocess_exec(..., stdout=PIPE, stderr=PIPE)`.
     - Return `StartResult(engine_handle=str(proc.pid), internal_port=port, inference_url=f"http://<hostname>:{port}/v1")`.
   - `stop(handle)`:
     - `os.kill(int(handle), SIGTERM)`; wait up to 30s; `SIGKILL` if not exited.
2. The engine selection happens in `deploy.py`:
   ```python
   from ..config import get_settings
   mode = get_settings().agent_runtime_mode
   engine = VllmContainerAdapter() if mode == "docker" else VllmSubprocessAdapter()
   ```
3. Log tail uses `tail_process(proc)` (already in T044's `log_tail.py`).
4. Health check (`wait_until_ready`) uses the same `/v1/models` poll loop.

## Acceptance Criteria

- [ ] In `systemd` mode, deploy commands launch vLLM via subprocess instead of a Docker container.
- [ ] `CUDA_VISIBLE_DEVICES` is set correctly so the process sees only the assigned GPUs.
- [ ] Stop signals the process cleanly; falls back to SIGKILL after 30s.
- [ ] Logs stream over the same WS pipeline as container mode.
- [ ] Auto-iteration (T042) works equivalently against the subprocess adapter.
- [ ] Tests verify the spawn command, env vars, and stop behavior.

## Out of Scope

- systemd unit + bare-metal install runbook — T055.
- Multiple-Python-venv selection (different engine versions per deployment) — backlog for v2 when more engines land.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
