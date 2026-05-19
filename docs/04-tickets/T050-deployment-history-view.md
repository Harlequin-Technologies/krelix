# T050 — Deployment history view with filters

**Status:** Not started
**Phase:** 11 — Frontend polish + deployment history
**Estimated session length:** 2 hr
**Depends on:** T039, T040
**Blocks:** None
**Maps to:** US-S-03 (basic record of past deployment attempts).

---

## Objective

Polish the `/deployments` list view from T040 into a proper history view: filter by status (multi-select), endpoint, model, date range; group by date; show key metadata (duration, iteration_count, fit prediction vs. observed outcome). Deployments are never deleted, so this is the operator's durable audit trail.

## Files to modify

- `frontend/src/pages/DeploymentsPage.tsx` — major refactor for filters + grouping

## Files to create

- `frontend/src/pages/deployments/DeploymentHistoryFilters.tsx`
- `frontend/src/pages/deployments/DeploymentHistoryTable.tsx`

## Steps

1. Filter bar: status multi-select, endpoint dropdown, model search (autocomplete), date range (from/to).
2. Table groups by date (a header row per day: "Today, Yesterday, 2026-05-15", etc.).
3. Columns: time of day, model + revision (linked), endpoint, status badge, iteration count, fit-prediction vs. observed-outcome comparison (e.g., "predicted: fits / observed: fit" → green check; mismatch → yellow indicator), duration if completed.
4. Click row → navigates to the deployment detail page.

## Acceptance Criteria

- [ ] Filters work for each dimension.
- [ ] Filter state is reflected in URL params (so back/forward and shareable links work).
- [ ] Date grouping is sensible.
- [ ] Fit-prediction vs. observed mismatch is visible at a glance.
- [ ] Pagination works for large history (loads more on scroll, or "load more" button).

## Out of Scope

- Export to CSV — backlog.
- Fit-prediction accuracy summary metric on this page — that's part of T058 measurement runbook, not a UI widget for v1.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
