# T053 — Endpoint detail polish: resolved config + GPU panel layout

**Status:** Not started
**Phase:** 11 — Frontend polish + deployment history
**Estimated session length:** 2 hr
**Depends on:** T026, T030, T049
**Blocks:** None
**Maps to:** US-M-07 (status visibility); foundation for v2 D-phase dashboards.

---

## Objective

Polish the endpoint list/detail UX so each endpoint row expands into a meaningful detail view: resolved config (showing which fields are from globals vs. overrides), live GPU panel (T030), artifacts panel (T049), and recent deployments. This is the layout that v2 will hang the realtime monitoring dashboards on.

## Files to modify

- `frontend/src/pages/endpoints/EndpointListView.tsx` — expandable row shows the new tabbed detail view

## Files to create

- `frontend/src/pages/endpoints/EndpointDetailTabs.tsx` — tabs for: Resolved Config, GPUs (live), Artifacts, Recent Deployments
- `frontend/src/pages/endpoints/ResolvedConfigView.tsx` — show each resolved field with a small "global default" or "override" badge

## Steps

1. `EndpointDetailTabs` — controlled tabs (plain Tailwind, no extra deps).
2. `ResolvedConfigView` — read `endpoint.resolved_config` and the underlying endpoint row's override fields; for each field, show: name, resolved value, source ("global" or "override"). Override rows have an inline "Clear override" link that calls PATCH with null for that field.
3. The Live GPUs tab embeds `LiveGpuPanel` from T030.
4. Artifacts tab embeds `EndpointArtifactsPanel` from T049.
5. Recent Deployments tab shows the last 10 deployments for this endpoint, linking to the deployment detail page.

## Acceptance Criteria

- [ ] Endpoint row expands into a four-tab detail view.
- [ ] Resolved config clearly distinguishes override vs. global per field.
- [ ] Inline "Clear override" works (PATCHes the endpoint with null for that field).
- [ ] All four tabs render usefully even when the agent is offline (graceful degradation messages).

## Out of Scope

- Persistent time-series charts on the GPU tab — v2 D-phase.
- Cross-endpoint comparison view — v2.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
