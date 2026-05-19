# T052 — Download progress + initial-config override UX

**Status:** Not started
**Phase:** 11 — Frontend polish + deployment history
**Estimated session length:** 2 hr
**Depends on:** T040, T044
**Blocks:** None
**Maps to:** US-C-01 (download progress), US-C-02 (config override).

---

## Objective

Two "Could" features from user-stories.md that polish the deploy experience: live download progress on the deployment detail page (current bytes/total + ETA), and a clean UI for overriding initial vLLM args at deploy time.

## Files to modify

- `frontend/src/pages/deployments/DeploymentDetailPage.tsx` — add download progress when status=`downloading`
- `frontend/src/pages/deployments/DeployDrawer.tsx` — collapsible "Advanced" section with config override editor

## Files to create

- `frontend/src/pages/deployments/DownloadProgressBar.tsx`
- `frontend/src/pages/deployments/ConfigOverrideEditor.tsx`

## Steps

1. Agent already sends `deployment_status` frames with `downloading` status; extend the payload to include `downloaded_bytes` and `total_bytes` (this requires a small backend + agent update — note in completion summary). Frontend displays a progress bar with ETA.
2. `ConfigOverrideEditor` — a key-value editor for vLLM args. Smart defaults shown for common args (`max_model_len`, `gpu_memory_utilization`, `tensor_parallel_size`, `quantization`); free-form add for advanced users. Validates that values are JSON-serializable.
3. Submit-time: overrides go into `initial_config_overrides` on the POST body.

## Acceptance Criteria

- [ ] Live download progress bar updates within ~1s of new bytes.
- [ ] ETA is rough but useful (no "10000 hours remaining" jankiness).
- [ ] Config override editor lets the operator add/edit/remove args at deploy time.
- [ ] Overrides are passed to the backend and end up in the initial vLLM launch args.

## Out of Scope

- A library of preset configs ("LoRA preset," "FP8 preset") — backlog.
- Save-as-default-for-this-model — backlog.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
