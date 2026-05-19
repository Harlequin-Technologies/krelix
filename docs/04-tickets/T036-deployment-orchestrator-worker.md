# T036 — Deployment orchestrator arq job + send deploy command to agent

**Status:** Not started
**Phase:** 7 — Deployment happy path
**Estimated session length:** 2.5 hr
**Depends on:** T025, T035
**Blocks:** T037 (agent side), T038 (status reporting)
**Maps to:** `api-contracts.md` `/agent/v1/stream` `deploy` frame; deployment lifecycle in `architecture.md`.

---

## Objective

Implement the `orchestrate_deployment(deployment_id)` arq job. The worker: re-reads the deployment + endpoint config, finds the agent's connected WebSocket in `AgentRegistry` (T025), and sends a `deploy` command frame over the WS. Updates `deployment.status` to `provisioning` and writes a `deployment_event` row. Subsequent updates (downloading → running) are driven by frames the agent sends back (T038).

## Files to modify

- `backend/src/krelix/worker_jobs/orchestrate_deployment.py` — replace the stub from T035 with the real implementation
- `backend/src/krelix/services/agent_registry.py` — add a `send_command(endpoint_id, frame)` helper

## Files to create

- `backend/tests/test_orchestrate_deployment.py` — uses a fake agent socket to verify the deploy frame is sent

## Steps

1. `AgentRegistry.send_command(endpoint_id, frame)` — looks up the connection, sends JSON frame, returns success/failure. If no connection, raises `AgentNotConnected`.
2. `orchestrate_deployment(ctx, deployment_id)`:
   - Open a session (via arq's connection or a manual `_session_factory()`).
   - Load deployment + endpoint + model + resolved config.
   - Generate a command id (UUID).
   - Build the `deploy` command frame payload: `{deployment_id, model_ref, resolved_revision, gpu_indices, initial_config, retry_budget, hot_tier_path, vault_mount_path}`.
   - `send_command(endpoint.id, {type: "deploy", id: cmd_id, payload: {...}})`.
   - If `AgentNotConnected`: mark deployment as `failed` with `failure_reason = "agent_not_connected_at_dispatch"`. Write a `deployment_event`. Done.
   - Else: update `deployment.status = 'provisioning'`. Write a `status_changed` event. Done.
   - Note: the job does NOT wait for the deploy to finish — the agent will send `deployment_status` frames asynchronously (T038), and the control plane's WS handler updates the deployment row when those arrive.
3. Tests use a fake WebSocket (a simple coroutine that records sent frames) injected into the `AgentRegistry` to verify the frame shape.

## Acceptance Criteria

- [ ] `orchestrate_deployment` arq job exists and is registered in `WorkerSettings.functions`.
- [ ] Job sends the correctly-shaped `deploy` frame to the agent via the registry.
- [ ] On agent-not-connected: deployment marked `failed` with the right `failure_reason`.
- [ ] On success: deployment status moves to `provisioning`, a `deployment_event` is written.
- [ ] Test verifies frame payload contains all required fields per `api-contracts.md`.

## Out of Scope

- Agent-side handling of the frame — T037.
- Status update reception — T038.
- Auto-iteration — T042.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
