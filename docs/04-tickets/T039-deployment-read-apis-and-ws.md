# T039 — Deployment read APIs + status WebSocket + stop endpoint

**Status:** Not started
**Phase:** 7 — Deployment happy path
**Estimated session length:** 2.5 hr
**Depends on:** T035, T038
**Blocks:** T040, T046 (log streaming UI)
**Maps to:** `api-contracts.md` `GET /api/v1/deployments`, `GET /api/v1/deployments/{id}`, `POST /api/v1/deployments/{id}/stop`, `GET /api/v1/deployments/{id}/events`, `WS /api/v1/deployments/{id}/status`.

---

## Objective

Round out the deployment API: list with filters, get by id, stop, events, and the operator-facing live status WebSocket.

## Files to modify

- `backend/src/krelix/api/v1/deployments.py` — add the additional routes
- `backend/src/krelix/api/v1/schemas/deployment.py` — add response shapes for list / events / status frames

## Files to create

- `backend/tests/test_deployment_read_api.py`

## Steps

1. `GET /api/v1/deployments` — filters: status (multi), endpoint_id, model_id, since. Pagination (limit/cursor or limit-only — match other list endpoints).
2. `GET /api/v1/deployments/{id}` — full record.
3. `POST /api/v1/deployments/{id}/stop` — validates the deployment is stoppable (status not terminal). Sends `stop_deployment` command to the agent via `AgentRegistry.send_command`. Returns 202. The agent's stop handler (T037) eventually sends back `deployment_status` with status=`stopped`, which T038 records.
4. `GET /api/v1/deployments/{id}/events` — paginated event list with `since` filter.
5. `WS /api/v1/deployments/{id}/status`:
   - Operator session auth on upgrade.
   - Subscribes to `krelix:events:deployment_status:<id>` Redis channel.
   - Initial frame on connect: current deployment state (snapshot, so the UI doesn't need a separate fetch).
   - Forwards subsequent events.

## Acceptance Criteria

- [ ] All five routes function per `api-contracts.md` shapes.
- [ ] POST /stop returns 409 `deployment_not_stoppable` for terminal-status deployments.
- [ ] WS `/status` emits the current state on connect and pushes subsequent updates within ~100ms of the agent reporting.
- [ ] Filters on the list endpoint work correctly (status array, endpoint_id, since).
- [ ] Events endpoint pagination works.
- [ ] All operator routes require auth + (for POST/stop) CSRF.

## Out of Scope

- Log streaming — T044/T045.
- Iteration event surfacing in UI — T043.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
