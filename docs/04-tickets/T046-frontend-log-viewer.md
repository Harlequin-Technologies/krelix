# T046 — Frontend log viewer with live tail

**Status:** Not started
**Phase:** 9 — Log streaming
**Estimated session length:** 2.5 hr
**Depends on:** T040, T045
**Blocks:** None
**Maps to:** US-M-08.

---

## Objective

Replace the placeholder log section in `DeploymentDetailPage.tsx` with a real live-tail log viewer using EventSource. Auto-scroll to bottom unless the operator has scrolled up; "Pause" toggle freezes the stream; download-all button exports the visible buffer.

## Files to create

- `frontend/src/pages/deployments/LogViewer.tsx`
- `frontend/src/hooks/useDeploymentLogs.ts` — EventSource wrapper

## Files to modify

- `frontend/src/pages/deployments/DeploymentDetailPage.tsx` — embed `LogViewer`

## Steps

1. `useDeploymentLogs(deploymentId, opts: {fromLastN: number, paused: boolean})`:
   - Opens an `EventSource` to `/api/v1/deployments/{id}/logs?from=last-N`.
   - On each `log` event, appends to a state array (capped at 5000 lines client-side to bound memory).
   - When `paused`: closes the EventSource; resuming re-opens it (skipping any missed lines for v1; surface a small "log gap" indicator).
2. `LogViewer.tsx`:
   - Pre-styled scrolling box with monospaced font.
   - Each line color-coded by stream (stderr in light red).
   - Auto-scroll to bottom when at-bottom; if operator scrolls up, freeze and show a "Jump to latest" button.
   - Pause / Resume toggle.
   - "Download" button serializes the current buffer to a `.log` file.

## Acceptance Criteria

- [ ] Log viewer streams live vLLM stdout/stderr from the SSE endpoint.
- [ ] Auto-scroll-to-bottom behavior works correctly (sticky to bottom; releases when operator scrolls up).
- [ ] Pause / Resume work.
- [ ] Download produces a sensible `.log` file containing the visible buffer.
- [ ] EventSource closes cleanly on page navigation away.

## Out of Scope

- Log search / filter — not v1.
- Multi-deployment combined log view — not v1.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
