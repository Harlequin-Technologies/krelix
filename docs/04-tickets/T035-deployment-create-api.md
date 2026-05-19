# T035 — Deployment create API (POST /api/v1/deployments) + arq job enqueue

**Status:** Not started
**Phase:** 7 — Deployment happy path
**Estimated session length:** 2.5 hr
**Depends on:** T010, T011, T023, T030, T032, T033
**Blocks:** T036, T039, T040
**Maps to:** `api-contracts.md` `POST /api/v1/deployments`; US-M-05.

---

## Objective

Implement `POST /api/v1/deployments`: validate the request, resolve the HF revision, snapshot the fit prediction onto the `deployment` row, create the row in `pending` state, enqueue an `orchestrate_deployment(deployment_id)` arq job. Synchronous response is 202 with the new deployment record (status pending).

## Files to create

- `backend/src/krelix/api/v1/deployments.py` — POST route (other deployment routes land in T039)
- `backend/src/krelix/api/v1/schemas/deployment.py` — request + response shapes
- `backend/src/krelix/worker_jobs/__init__.py` — package
- `backend/src/krelix/worker_jobs/orchestrate_deployment.py` — empty arq function stub (real logic in T036)
- `backend/tests/test_deployment_create_api.py`

## Files to modify

- `backend/src/krelix/worker.py` — register `orchestrate_deployment` in `WorkerSettings.functions`
- `backend/src/krelix/api/v1/router.py` — include deployments router

## Steps

1. Request schema: `DeploymentCreateRequest` with `endpoint_id`, `model_ref`, optional `model_revision`, optional `gpu_indices`, optional `initial_config_overrides`.
2. Logic:
   - Look up endpoint (404 if not found, 409 if soft-deleted or `agent_status != 'online'`).
   - Upsert model row via T032's `upsert_model_from_hf`.
   - Resolve revision via T032's `resolve_revision` (or use provided `model_revision`).
   - Compute fit prediction via T033 (record prediction + basis on the deployment row).
   - If prediction is `wont_fit`: 409 `endpoint_has_no_capacity`.
   - If `gpu_indices` provided: validate against actual `gpu_resource` rows for the endpoint (422 `invalid_gpu_indices`).
   - Pick initial config (a small helper module — `services/initial_vllm_config.py` — picks reasonable defaults: `--quantization` from model.primary_quantization, `--max-model-len` heuristic based on VRAM, `--gpu-memory-utilization 0.85`, etc.). Merge in `initial_config_overrides`.
   - Insert `deployment` row with status=`pending`, initial_config, fit_prediction_at_initiation, fit_prediction_basis.
   - Enqueue `orchestrate_deployment(deployment_id)` arq job.
   - Return 202 with the deployment record.

## Acceptance Criteria

- [ ] POST creates the deployment row and enqueues the arq job; response is 202.
- [ ] Validation: agent offline → 409; `wont_fit` prediction → 409; invalid gpu_indices → 422; model not on HF → 404.
- [ ] Fit prediction is recorded on the deployment row.
- [ ] Initial config is selected by `initial_vllm_config` helper and is JSON-serializable.
- [ ] `gpu_indices` defaults to selecting the largest-free-VRAM single GPU on the endpoint (per T033 prediction basis).
- [ ] Auth required; CSRF required.

## Out of Scope

- Job execution itself — T036.
- Status updates / WS events — T038/T039.
- The auto-iteration loop — T042.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
