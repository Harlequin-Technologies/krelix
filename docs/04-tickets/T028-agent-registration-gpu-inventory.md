# T028 — Agent registration flow + GPU/MIG inventory via pynvml

**Status:** Not started
**Phase:** 5 — Host agent skeleton (container mode)
**Estimated session length:** 3 hr
**Depends on:** T024, T027
**Blocks:** T029
**Maps to:** `api-contracts.md` `POST /agent/v1/register` (client side); `architecture.md` Component 5 GPU introspection; `data-model.md` MIG handling.

---

## Objective

Implement the agent's registration: discover local GPUs (and MIG instances) via `pynvml`, gather host info, POST `/agent/v1/register` with the agent's token. On success, store the returned `endpoint_id`, `resolved_config`, and `stream_url` in agent runtime state (in-memory) for use by the WebSocket client (T029).

## Read for context

- [`../03-technical/api-contracts.md`](../03-technical/api-contracts.md) — `/agent/v1/register` request + response
- [`../03-technical/data-model.md`](../03-technical/data-model.md) — MIG handling (each MIG instance reported as its own gpu_resource)
- [`T024-agent-bearer-auth-registration.md`](T024-agent-bearer-auth-registration.md) — server side

## Files to create

- `agent/src/krelix_agent/gpu.py` — pynvml inventory (detects MIG, reports each instance)
- `agent/src/krelix_agent/host_info.py` — hostname, OS, kernel, docker version, nvidia driver
- `agent/src/krelix_agent/register.py` — register() coroutine
- `agent/src/krelix_agent/state.py` — `AgentState` dataclass (endpoint_id, resolved_config, stream_url, engines_available)
- `agent/tests/test_gpu.py` — mock pynvml, verify report shape (including MIG)
- `agent/tests/test_register.py` — mock HTTP client, verify request payload + response handling

## Steps

1. `gpu.py`:
   - On import, try `pynvml.nvmlInit()`. If it fails (no NVIDIA driver), log a clear error and return empty list.
   - For each physical GPU: report `mig_capable` from `nvmlDeviceGetMigMode`, `mig_enabled_on_parent` from current MIG state. If MIG enabled, iterate `nvmlDeviceGetMigDeviceHandleByIndex` and report each instance (with `mig_profile` from `nvmlDeviceGetMigDeviceHandle` info — exact NVML calls vary by driver version; check docs at implementation time). If MIG not enabled, report the whole GPU as a single row.
2. `host_info.py`: `socket.gethostname()`, `platform.system()`, `platform.release()`, optional `docker version` shell-out (container mode only), NVML driver version.
3. `engines_available`: in container mode, hardcode `[{name: "vllm", version: None, launcher: "container:vllm/vllm-openai:latest"}]` for v1 (the image tag is configurable but defaults to the latest vLLM-Openai image). In systemd mode, use `KRELIX_ENGINE_VLLM_PYTHON` + `KRELIX_ENGINE_VLLM_MODULE` to construct `"subprocess:<python> -m <module>"`.
4. `register.py`: build request payload, POST with `httpx.AsyncClient`, Bearer auth, parse response, populate `AgentState`. Retry on 5xx with exponential backoff up to 5 attempts; fail fast on 401 / 4xx with clear log + exit.
5. Update `cli.py` `register` command to actually run `await register()` and print the result.
6. Tests use `pytest-httpx` (add dev dep) to mock the control plane.

## Acceptance Criteria

- [ ] GPU inventory handles both MIG-disabled and MIG-enabled physical GPUs.
- [ ] Each MIG instance is reported with its own NVML UUID and `parent_nvml_uuid` pointing to the parent.
- [ ] No NVIDIA driver present → agent logs error + exits with non-zero code.
- [ ] Successful POST `/agent/v1/register` populates `AgentState` and returns; 401 → exits with clear message.
- [ ] 5xx errors trigger exponential backoff retry up to 5 attempts.
- [ ] `engines_available` is correctly reported based on runtime mode.

## Out of Scope

- WebSocket connection (T029); periodic re-registration on token rotation (operator regenerates and restarts agent in v1)

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
