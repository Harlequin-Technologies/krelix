# T038 — Control plane: handle deployment_status frames from agent → update DB + fan out

**Status:** Not started
**Phase:** 7 — Deployment happy path
**Estimated session length:** 2 hr
**Depends on:** T025, T037
**Blocks:** T039, T040
**Maps to:** Server-side handling of `deployment_status` frames; `data-model.md` `deployment` + `deployment_event`.

---

## Objective

Extend the control plane's agent WS handler (`api/agent/v1/stream.py` from T025) to handle `deployment_status` frames from agents: update the corresponding `deployment` row's status, write a `deployment_event`, and publish to a Redis pub/sub channel so operator-facing WS clients (T039) can subscribe.

## Files to modify

- `backend/src/krelix/api/agent/v1/stream.py` — add `deployment_status` handling
- `backend/src/krelix/services/event_fanout.py` (from T030) — add `publish_deployment_status` helper

## Files to create

- `backend/src/krelix/services/deployment_state.py` — `apply_status_update(deployment_id, frame)` writes DB changes atomically
- `backend/tests/test_deployment_status_flow.py` — integration

## Steps

1. `deployment_state.apply_status_update`:
   - Open session; load deployment row.
   - Validate status transition (e.g., reject `failed → running` — terminal status is sticky).
   - Update status; if `running`: set `started_at`, `inference_url`, `internal_port`, `engine_handle`, `engine_runtime_mode`, `final_config`, set `observed_outcome` based on the actual deployment + GPU state (e.g., `fit` if it succeeded without offload).
   - If `failed`: set `failed_at`, `failure_reason`.
   - If `stopped`: set `stopped_at`.
   - Write `deployment_event` row with the `event_type=status_changed`, `from_status`, `to_status`, `payload`.
   - Commit.
2. In `stream.py`, add handling for `deployment_status` frame type:
   - Validate payload shape.
   - Call `apply_status_update`.
   - Publish to Redis channel `krelix:events:deployment_status:<deployment_id>` and to a global `krelix:events:deployment_status_any` channel for dashboards.
   - Ack the frame.

## Acceptance Criteria

- [ ] `deployment_status` frames update the deployment row correctly.
- [ ] Terminal status transitions are immutable (e.g., a late `running` frame for an already-`failed` deployment is ignored with a structured log warning).
- [ ] Each status update writes a `deployment_event` row.
- [ ] Updates are published to Redis for downstream fanout.
- [ ] `observed_outcome` is set correctly when the deployment succeeds.
- [ ] Integration test: simulate the full happy-path frame sequence and verify the DB state matches.

## Out of Scope

- Operator-facing WS endpoint (T039) consumes these published events.
- Iteration events — T043.
- Log frames — T044/T045.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
