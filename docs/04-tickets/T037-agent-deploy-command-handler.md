# T037 — Agent deploy command handler: download model + launch vLLM container

**Status:** Not started
**Phase:** 7 — Deployment happy path
**Estimated session length:** 4 hr
**Depends on:** T029, T036
**Blocks:** T038 (status reporting), T042 (auto-iteration extends this), T047 (two-tier extends this)
**Maps to:** Agent-side of the `deploy` command frame; container-mode engine launch via Docker socket.

---

## Objective

In the agent's `_recv_loop` (T029), handle the `deploy` command frame: ack it, then run an async coroutine that downloads the model from HF to the hot tier and launches a vLLM container via the local Docker socket. Send back `deployment_status` frames as the state evolves (downloading → starting → running or failed). **No auto-iteration yet** — single attempt only. **No two-tier vault flow yet** — just download-to-hot then launch.

## Files to create

- `agent/src/krelix_agent/commands/__init__.py` — empty
- `agent/src/krelix_agent/commands/deploy.py` — `handle_deploy(payload)` coroutine
- `agent/src/krelix_agent/storage.py` — hot-tier path helpers (canonical layout)
- `agent/src/krelix_agent/downloader.py` — wraps `huggingface_hub.snapshot_download` async via `asyncio.to_thread`
- `agent/src/krelix_agent/engines/__init__.py` — empty
- `agent/src/krelix_agent/engines/base.py` — `EngineAdapter` protocol
- `agent/src/krelix_agent/engines/vllm_container.py` — `VllmContainerAdapter` — launches a vLLM Docker container via `docker-py`
- `agent/tests/test_deploy_flow.py` — integration with mocked Docker + HF

## Files to modify

- `agent/src/krelix_agent/stream.py` — route `type: "deploy"` frames to `handle_deploy`

## Steps

1. `storage.py`:
   - `hot_tier_path_for(hot_tier_root, hf_model_ref, resolved_revision) -> Path` — canonical layout: `<hot_tier_root>/<safe-ref>/<revision>/` (with `safe-ref` = ref with `/` replaced by `--`).
   - `vault_path_for(vault_root, ...)` analogous (used in T047).
2. `downloader.py`:
   - `download_to_hot(hf_token, hf_model_ref, resolved_revision, hot_tier_path) -> int (bytes downloaded)`:
     - Uses `huggingface_hub.snapshot_download(repo_id=..., revision=..., local_dir=...)`.
     - Streams progress via `tqdm` callbacks → emits `deployment_status` frames with status=`downloading` and a percent estimate (best-effort).
     - Returns bytes downloaded.
3. `engines/base.py` — `EngineAdapter` protocol with `async def start(deployment_id, model_path, gpu_indices, args) -> StartResult` and `async def stop(handle) -> None`. `StartResult` carries `engine_handle`, `internal_port`, `inference_url`.
4. `engines/vllm_container.py`:
   - `start()`: pick a free host-side port, build `docker.client.containers.run(...)` call with the vLLM image, GPUs mapped, hot-tier dir bind-mounted read-only, args from `initial_config`, environment vars as needed. Run container detached.
   - `stop()`: stop + remove the container by id.
5. `commands/deploy.py`:
   - Acks the frame (`{"type": "ack", "id": cmd_id, "payload": {"result": "accepted"}}`).
   - In a background task: send `deployment_status` frames for each transition.
   - Steps: ensure hot-tier dir exists → download from HF → status: `starting` → engine.start() → wait briefly for the vLLM container's `/v1/models` endpoint to respond OK (curl-style health check, up to 90s) → on success: send status=`running` with `engine_handle` + `internal_port` + `inference_url`. On any failure: send status=`failed` with `failure_reason`.
6. Inference URL: `http://<hostname>:<internal_port>/v1` — `hostname` is the agent host's hostname (reported in `host_info` during registration).

## Acceptance Criteria

- [ ] Receiving a `deploy` frame triggers the full pipeline in a background task; the WS recv loop is not blocked.
- [ ] Frames sent back: at least `downloading` → `starting` → `running` (or `failed`).
- [ ] Successful deployment yields a vLLM container running and reachable on the published port.
- [ ] `inference_url` is reported correctly.
- [ ] Failure surfaces a `failed` status with `failure_reason` populated.
- [ ] `EngineAdapter` protocol is in place so T054 can add `VllmSubprocessAdapter`.
- [ ] Tests with mocked Docker + mocked HF verify the frame shape and call sequence.

## Out of Scope

- Auto-iteration on failure — T042 (single attempt only in this ticket).
- Two-tier vault copy — T047.
- Log streaming — T044.
- Eject — T037 is start-only; stop comes via the `stop_deployment` frame (which T035-era POST stop will trigger). Add a minimal `stop_deployment` frame handler here OR push to a tiny separate ticket — **decision: handle it here** since it's small and the lifecycle pairs cleanly.

## Notes

- The vLLM Docker image: default to `vllm/vllm-openai:latest`; the image tag may need to be pinned per the engine version recorded in the deployment. For v1, the agent picks the latest stable; the deployment.engine_version is reported back from the running container's `/version` endpoint.
- The health check (waiting for vLLM to be ready) is a real concern — vLLM can take 1-5 minutes to load a large model. Poll `/v1/models` with a generous timeout (5 minutes default, configurable).

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
