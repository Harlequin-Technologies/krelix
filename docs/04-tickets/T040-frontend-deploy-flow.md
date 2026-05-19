# T040 — Frontend deploy flow + deployments list + live status

**Status:** Not started
**Phase:** 7 — Deployment happy path
**Estimated session length:** 4 hr
**Depends on:** T020, T034, T035, T039
**Blocks:** None in Phase 7
**Maps to:** US-M-05, US-M-06, US-M-07, US-M-09.

---

## Objective

Wire the deploy flow end-to-end in the UI: a "Deploy" button on the model detail page opens a drawer to pick endpoint + (optional) gpu_indices + (optional) config overrides; submit calls `POST /api/v1/deployments` and navigates to a deployment detail page that subscribes to the live status WS. Also add the `/deployments` list page.

## Files to create

- `frontend/src/pages/DeploymentsPage.tsx` — list view
- `frontend/src/pages/deployments/DeploymentDetailPage.tsx` — `/deployments/:id`
- `frontend/src/pages/deployments/DeployDrawer.tsx` — opened from the model detail page
- `frontend/src/hooks/useDeployments.ts` (list, get, create, stop)
- `frontend/src/hooks/useDeploymentStatusLive.ts` (WS to `/status`)

## Files to modify

- `frontend/src/router.tsx` — add `/deployments`, `/deployments/:id`
- `frontend/src/layouts/AppLayout.tsx` — wire "Deployments" nav link
- `frontend/src/pages/models/ModelDetailPage.tsx` — make the "Deploy" CTA real

## Steps

1. `DeployDrawer.tsx`:
   - Form: endpoint dropdown (filter to online endpoints), GPU picker (per-endpoint GPUs; default "auto"), optional config-override textarea (advanced; default collapsed).
   - Shows live fit prediction for the selected endpoint as user picks.
   - Submit → POST → navigate to `/deployments/<new_id>`.
   - Errors from the API surface inline.
2. `DeploymentDetailPage.tsx`:
   - Top section: model name + revision (linked), endpoint, status badge with live colors, started/stopped timestamps.
   - Live updates via `useDeploymentStatusLive`.
   - When status reaches `running`: prominent "Inference URL" block with copy button + `curl` example.
   - "Stop" button (calls POST /stop, confirms first).
   - Below: an Events list (paginated `/events`).
   - Log viewer is a placeholder ("logs in next phase") — real log UI lands in T046.
3. `DeploymentsPage.tsx`:
   - Table: model + revision, endpoint, status (color-coded), initiated, started/stopped, actions (view, stop if stoppable).
   - Filters: status, endpoint, date range.

## Acceptance Criteria

- [ ] Operator can: pick a model → click Deploy → choose endpoint → submit → land on deployment detail page → see status transition `pending → provisioning → downloading → starting → running` live.
- [ ] When `running`: inference URL is shown with a working copy button; `curl` example uses the actual URL.
- [ ] Stop button works for running/starting deployments; confirms first; status transitions to `stopped`.
- [ ] Deployments list page shows all deployments with filters.
- [ ] Live WS updates within ~100ms of agent reports.
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm test` exit 0.

## Out of Scope

- Log viewer — T046.
- Download progress display — T052.
- Auto-iteration visualization — T043 fronted into T046 or here as a small follow-up.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
