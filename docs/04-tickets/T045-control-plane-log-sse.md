# T045 — Control plane SSE endpoint + log buffer

**Status:** Not started
**Phase:** 9 — Log streaming
**Estimated session length:** 2 hr
**Depends on:** T038, T044
**Blocks:** T046
**Maps to:** `api-contracts.md` `SSE /api/v1/deployments/{id}/logs`.

---

## Objective

Implement `SSE /api/v1/deployments/{id}/logs`: maintains a rolling log buffer per deployment in Redis (last ~5000 lines or 1 MB, whichever first), supports `?from=last-N` for initial flush, then streams live additions.

## Files to modify

- `backend/src/krelix/api/agent/v1/stream.py` — handle `deployment_log` frames: append to Redis list (`krelix:logs:<deployment_id>`, capped via `LTRIM`); publish to `krelix:events:log:<deployment_id>` for live fanout

## Files to create

- `backend/src/krelix/api/v1/deployment_logs.py` — `SSE /api/v1/deployments/{id}/logs`
- `backend/tests/test_log_sse.py`

## Steps

1. In `stream.py` `deployment_log` handler:
   - `LPUSH krelix:logs:<id> <json>` then `LTRIM krelix:logs:<id> 0 4999` (keep newest 5000).
   - `PUBLISH krelix:events:log:<id> <json>` for live subscribers.
2. SSE endpoint:
   - Operator auth on the request.
   - `?from=last-N` (default 200) — `LRANGE krelix:logs:<id> 0 N-1`, reverse, emit each as `event: log` SSE frame.
   - Then subscribe to `krelix:events:log:<id>` and forward each new message.
   - Headers: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`.
   - Handle client disconnect cleanly (unsubscribe Redis).

## Acceptance Criteria

- [ ] `deployment_log` frames are persisted to a per-deployment Redis list capped at 5000 entries.
- [ ] SSE endpoint emits initial buffer (last N) then live tail.
- [ ] Multiple SSE clients on the same deployment receive the same live stream.
- [ ] Client disconnect releases the Redis subscription.
- [ ] Auth required on the SSE route.
- [ ] No log content is logged at info level (preserve structlog redaction posture).

## Out of Scope

- Log search / filter — not v1.
- Long-term log archive — backlog.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
