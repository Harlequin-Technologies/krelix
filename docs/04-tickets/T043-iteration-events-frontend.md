# T043 — Iteration event reporting on control plane + frontend display

**Status:** Not started
**Phase:** 8 — Auto-iteration loop
**Estimated session length:** 1.5 hr
**Depends on:** T038, T042
**Blocks:** None
**Maps to:** US-M-05 acceptance criteria; `data-model.md` `deployment.iteration_count` + `deployment_event`.

---

## Objective

Surface auto-iteration events visibly to the operator. Backend writes `deployment_event` rows with `event_type=iteration_attempt` whenever the agent's `deployment_status` frame carries iteration metadata; updates `deployment.iteration_count`. Frontend renders an iteration timeline on the deployment detail page so the operator can see "attempt 1 OOM at load → attempt 2 reduced gpu_memory_utilization → attempt 3 running."

## Files to modify

- `backend/src/krelix/services/deployment_state.py` — when the frame includes `iteration` payload, write an `iteration_attempt` event and increment `deployment.iteration_count`
- `frontend/src/pages/deployments/DeploymentDetailPage.tsx` — render the iteration timeline

## Files to create

- `frontend/src/pages/deployments/IterationTimeline.tsx`
- `backend/tests/test_iteration_events.py`

## Steps

1. Backend: in `apply_status_update`, if `frame.iteration` is present:
   - Write `deployment_event(event_type="iteration_attempt", payload={"attempt": ..., "reason": ..., "adjusted_args": ...})`.
   - Set `deployment.iteration_count = max(deployment.iteration_count, frame.iteration.attempt)`.
2. Frontend `IterationTimeline.tsx`:
   - Reads `/api/v1/deployments/{id}/events` filtered to `event_type=iteration_attempt`.
   - Renders a vertical timeline: attempt number, reason, adjusted args (diff badges), timestamp.
   - Placed above the Events list on the deployment detail page when any iteration events exist.

## Acceptance Criteria

- [ ] Iteration metadata in `deployment_status` frames is persisted as `deployment_event` rows.
- [ ] `deployment.iteration_count` reflects the highest attempt number seen.
- [ ] Frontend renders a clear iteration timeline showing each retry's reason and config diff.
- [ ] If a deployment had no iterations, the timeline is not displayed.

## Out of Scope

- Editing the catalog from the UI — not in v1.
- Iteration analytics dashboard — v2.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
