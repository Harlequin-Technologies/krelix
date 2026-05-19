# T029 — Agent WebSocket client + heartbeat loop + periodic GPU state push

**Status:** Not started
**Phase:** 5 — Host agent skeleton (container mode)
**Estimated session length:** 3 hr
**Depends on:** T025, T028
**Blocks:** T036 (deploy command handling)
**Maps to:** `api-contracts.md` `WS /agent/v1/stream` (client side); architecture WS framing.

---

## Objective

Implement the agent's persistent WebSocket client: connect to `stream_url` returned by registration, authenticate via the same bearer token, send `heartbeat` frames every N seconds (default 30s, configurable via T027), send `gpu_state` frames periodically (every 30s) with live VRAM/util data, ack any unknown frames cleanly. Reconnect with exponential backoff on disconnect.

## Files to create

- `agent/src/krelix_agent/stream.py` — `StreamClient` class
- `agent/src/krelix_agent/frames.py` — Envelope + frame schemas (mirror backend's)
- `agent/src/krelix_agent/gpu_state.py` — live GPU state queries (vram_used, util, temp, power via pynvml)
- `agent/tests/test_stream.py` — using a local fake WS server (or `pytest-asyncio` + `websockets.serve`)

## Steps

1. `frames.py` — same envelope shape as backend: `{type, id?, payload}`. Heartbeat + gpu_state payload models.
2. `gpu_state.py` — for each gpu_resource (including MIG instances), query `nvmlDeviceGetMemoryInfo`, `nvmlDeviceGetUtilizationRates`, `nvmlDeviceGetTemperature`, `nvmlDeviceGetPowerUsage`. Return list of dicts matching the `gpu_state` frame shape.
3. `stream.py` — `StreamClient` with:
   - `connect()` — opens WS with Authorization header; on success, transitions agent to "connected" state.
   - `_heartbeat_loop()` — every `heartbeat_interval_seconds`, send heartbeat frame with `stats` (free_disk on hot tier + vault if available — `shutil.disk_usage`).
   - `_gpu_state_loop()` — every 30s (same default), send `gpu_state` frames.
   - `_recv_loop()` — read frames; for unknown types in v1, send ack with `result: "rejected"`. Deploy commands etc. come in T036.
   - On disconnect: exponential backoff 1s → 60s, then reconnect.
4. Update `cli.py` `run` command: register → start `StreamClient` → run loops indefinitely; on SIGTERM, graceful shutdown.

## Acceptance Criteria

- [ ] Agent connects to `stream_url` with `Authorization: Bearer <token>` on the upgrade request.
- [ ] Heartbeat frames sent every 30s (configurable); control plane acks them.
- [ ] `gpu_state` frames sent every 30s with live VRAM used, GPU util, temperature, power.
- [ ] On disconnect, agent reconnects with exponential backoff up to 60s.
- [ ] Unknown server → agent frames acked with `result: "rejected"`.
- [ ] SIGTERM closes the WS cleanly (sends close frame, exits).
- [ ] Integration test: spin up backend in test, run agent in same process, verify heartbeat propagates to `endpoint.last_heartbeat_at`.

## Out of Scope

- Deploy/stop/eject command handling — T036
- Log streaming — T044
- vLLM container lifecycle — T037

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
