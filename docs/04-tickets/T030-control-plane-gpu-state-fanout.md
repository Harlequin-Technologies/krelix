# T030 — Control plane: route gpu_state frames + frontend live GPU display

**Status:** Not started
**Phase:** 5 — Host agent skeleton (container mode)
**Estimated session length:** 2.5 hr
**Depends on:** T025, T029
**Blocks:** Phase 11 dashboard work (D-phase)
**Maps to:** `api-contracts.md` `WS /api/v1/endpoints/{id}/gpus/live`.

---

## Objective

Wire `gpu_state` frames from the agent through the control plane to operator-facing UI clients. Backend adds the operator-facing WebSocket and uses Redis pub/sub to fan out frames from the agent's `_recv_loop` (in T025) to potentially multiple connected UI clients. Frontend adds a live GPU panel on the endpoint detail (or the endpoints list) showing live VRAM used + GPU util per GPU.

## Files to create (backend)

- `backend/src/krelix/api/v1/endpoints_live.py` — `WS /api/v1/endpoints/{id}/gpus/live`
- `backend/src/krelix/services/event_fanout.py` — Redis pub/sub helpers for "agent → operator UI" event channels

## Files to modify (backend)

- `backend/src/krelix/api/agent/v1/stream.py` — when a `gpu_state` frame is received, publish to `krelix:events:gpu_state:<endpoint_id>` in Redis
- `backend/src/krelix/api/v1/router.py` — include `endpoints_live`

## Files to create (frontend)

- `frontend/src/pages/endpoints/LiveGpuPanel.tsx` — subscribes to the WS, renders a per-GPU panel (VRAM used / total, util%, temp)
- `frontend/src/hooks/useEndpointGpusLive.ts` — WS hook with auto-reconnect

## Files to modify (frontend)

- `frontend/src/pages/endpoints/EndpointListView.tsx` — under each row, an expandable section showing the `LiveGpuPanel` for that endpoint
  - Alternatively, add an `/endpoints/:id` detail route — operator pick. Default to the expandable row for v1 simplicity.

## Steps

1. Backend `event_fanout.py`: publish/subscribe helpers around the Redis client.
2. In `stream.py` `_recv_loop`: when a `gpu_state` frame arrives, validate, then `redis.publish(f"krelix:events:gpu_state:{endpoint_id}", frame_json)`.
3. New WS endpoint `WS /api/v1/endpoints/{id}/gpus/live`:
   - Requires operator auth (session cookie). Implement via WS-compatible auth dependency that reads the session cookie from the upgrade headers.
   - Subscribes to `krelix:events:gpu_state:{id}` and forwards each message to the connected operator client as-is.
   - On disconnect, unsubscribes cleanly.
4. Frontend `useEndpointGpusLive(endpointId)` opens the WS to `/api/v1/endpoints/{id}/gpus/live`. Auto-reconnect with backoff. Returns the latest snapshot per GPU.
5. `LiveGpuPanel` renders one card per gpu_resource: GPU name, VRAM bar (used/total), GPU util %, temp °C, power W. Updates every frame.

## Acceptance Criteria

- [ ] When the agent sends `gpu_state` frames, they're published to Redis under per-endpoint channels.
- [ ] Operator-facing `WS /api/v1/endpoints/{id}/gpus/live` subscribes to those channels and forwards frames to all connected UI clients.
- [ ] WS endpoint requires operator session auth — unauthenticated upgrade is rejected.
- [ ] Frontend shows live VRAM + util per GPU, updates within 1s of the agent's report.
- [ ] Multiple UI tabs open to the same endpoint receive the same updates independently.
- [ ] Disconnecting one UI tab doesn't affect others.

## Out of Scope

- Persistent time-series storage of metrics — v2 D-phase.
- Charts / graphs — Phase 11 polish (or v2). v1 shows current values only.
- Alarming on high temp / high util — not in v1.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
