# T051 — License + revision metadata badges across the UI

**Status:** Not started
**Phase:** 11 — Frontend polish + deployment history
**Estimated session length:** 1.5 hr
**Depends on:** T034, T040
**Blocks:** None
**Maps to:** US-S-01 (revision pinning), US-S-02 (license metadata at discovery + deployment time).

---

## Objective

Add consistent license + resolved-revision badges everywhere a model is mentioned in the UI: HF search results, model detail, deployment detail, deployment history, artifact list. Make license issues visible at a glance (color coding); make pinned revisions copyable.

## Files to create

- `frontend/src/components/LicenseBadge.tsx`
- `frontend/src/components/RevisionBadge.tsx`

## Files to modify

- `frontend/src/pages/ModelsPage.tsx`, `ModelDetailPage.tsx`, `DeploymentDetailPage.tsx`, `DeploymentHistoryTable.tsx`, `EndpointArtifactsPanel.tsx` — drop in the badges

## Steps

1. `LicenseBadge` — props: `license: string | null`, `gated: bool`. Color-coded: apache-2.0/mit/bsd → green; cc-by/cc-by-sa → blue; "other" or known restrictive → yellow; null → outline/red; gated → lock icon overlay regardless of license.
2. `RevisionBadge` — props: `revision: string` (40-char SHA). Display: first 8 chars; copy button for the full SHA.
3. Use both in the listed pages, consistently positioned.

## Acceptance Criteria

- [ ] Badges render consistently across all surfaces.
- [ ] License colors are predictable + documented (small README in `frontend/src/components/`).
- [ ] Revision badge shows truncated SHA with full-SHA copy.
- [ ] Gated models display the lock icon regardless of license.
- [ ] Missing license shows a clear visual warning.

## Out of Scope

- License compliance reporting (e.g., "all your running deployments under license X") — backlog.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
