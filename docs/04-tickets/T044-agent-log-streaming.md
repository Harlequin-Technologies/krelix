# T044 — Agent log capture from vLLM + log frames over WebSocket

**Status:** Not started
**Phase:** 9 — Log streaming
**Estimated session length:** 2.5 hr
**Depends on:** T037, T042
**Blocks:** T045, T046
**Maps to:** US-M-08; `api-contracts.md` `deployment_log` frame.

---

## Objective

Stream vLLM container/process stdout+stderr from the agent to the control plane in near-realtime. Reuse the `LogCapture` introduced in T042 — augment it so it also pushes each new line as a `deployment_log` frame on the WebSocket.

## Files to modify

- `agent/src/krelix_agent/commands/deploy.py` — start a tail task alongside the vLLM container/process that reads its logs and emits both into the in-memory buffer and as WS frames

## Files to create

- `agent/src/krelix_agent/log_tail.py` — `tail_container(container_id)` and `tail_process(proc)` async iterators over `(stream, line)` tuples
- `agent/tests/test_log_tail.py`

## Steps

1. `log_tail.py`:
   - `tail_container(docker_client, container_id) -> AsyncIterator[tuple[str, str]]` — uses `docker-py`'s `container.logs(stream=True, follow=True, ...)`; yields `("stdout"|"stderr", line)`.
   - `tail_process(proc) -> AsyncIterator[tuple[str, str]]` — reads from `proc.stdout` and `proc.stderr`; yields tuples.
2. In `deploy.py`, after engine.start(), spawn a background task that:
   - Iterates over the tail
   - Appends each line to `LogCapture`
   - Sends a `deployment_log` frame: `{type: "deployment_log", payload: {deployment_id, ts, stream, line}}`
3. Throttle: don't send more than ~50 frames/sec per deployment. If the engine logs a flood, batch into multi-line frames (`lines: [...]` instead of a single `line`) with a 100ms tick.
4. Stop the tail task when the deployment transitions to a terminal status or is ejected.

## Acceptance Criteria

- [ ] Logs from the running vLLM container/process flow as WS frames to the control plane.
- [ ] Log lines preserve their original stream (stdout vs stderr).
- [ ] Throttling prevents flooding the WS at >50 frames/sec.
- [ ] Tail task is correctly stopped on deployment terminal state.
- [ ] `LogCapture` (used by the iteration loop) still receives the same lines.

## Out of Scope

- Operator-facing log fanout — T045.
- Log archival / retention beyond the rolling buffer — backlog.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
