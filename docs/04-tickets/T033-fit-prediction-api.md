# T033 — Fit prediction logic + /api/v1/fit-predictions endpoint

**Status:** Not started
**Phase:** 6 — HuggingFace browsing + fit prediction
**Estimated session length:** 2.5 hr
**Depends on:** T030 (live GPU state), T032 (model cache)
**Blocks:** T034 (frontend), T035 (deploy records the prediction)
**Maps to:** `api-contracts.md` `GET /api/v1/fit-predictions`; success criterion #3 (≥90% prediction accuracy).

---

## Objective

Implement the server-side fit-prediction logic. Given a model and an endpoint, returns one of `fits_comfortably`, `needs_offload`, `wont_fit`, along with a `basis` JSONB capturing the numbers that drove the decision. Predictions are computed live, not cached.

## Files to create

- `backend/src/krelix/services/fit_prediction.py` — pure-function logic with the heuristic
- `backend/src/krelix/api/v1/fit_predictions.py` — the endpoint
- `backend/src/krelix/api/v1/schemas/fit_prediction.py`
- `backend/tests/test_fit_prediction_logic.py` — table-driven tests
- `backend/tests/test_fit_prediction_api.py`

## Steps

1. `services/fit_prediction.py` — function:
   ```python
   @dataclass
   class FitInputs:
       model_estimated_size_mb: int
       model_format: str | None   # 'safetensors' | 'gguf' | 'pt' | None
       model_quantization: str | None
       gpus: list[GpuFitData]      # each: vram_total_mb, vram_free_mb, model_name

   @dataclass
   class FitPrediction:
       outcome: Literal["fits_comfortably", "needs_offload", "wont_fit"]
       basis: dict[str, Any]

   def predict_fit(inputs: FitInputs) -> FitPrediction: ...
   ```
   Heuristic:
   - Compute `working_set_mb` = model_estimated_size_mb × overhead_factor (start at 1.25 — adjust during the 20-combo test set calibration in T058).
   - `largest_single_gpu_free_mb` = max(gpu.vram_free_mb for gpu in gpus).
   - `total_free_vram_mb` = sum(gpu.vram_free_mb for gpu in gpus).
   - If `working_set_mb <= largest_single_gpu_free_mb`: **fits_comfortably**.
   - Elif `working_set_mb <= total_free_vram_mb`: **needs_offload** (multi-GPU or CPU offload).
   - Else: **wont_fit**.
   - `basis` includes all input numbers and the resolved `working_set_mb`.
2. `api/v1/fit_predictions.py`:
   - `GET /api/v1/fit-predictions?model_ref=...&endpoint_id=...`:
     - Look up or upsert `model` row via T032.
     - Look up endpoint + gpu_resources.
     - Read live GPU state from Redis (the most recent `gpu_state` frame published by the agent — stored in a Redis key `krelix:gpu_state:<gpu_resource_id>` with short TTL; agent's T029 stream handler should also write to this key on every gpu_state frame so we have a cached snapshot).
     - If no recent state available (agent offline), return 409 `agent_not_connected`.
     - Build `FitInputs`, call `predict_fit`, return result.
3. **Side effect from T030 / T025:** the WebSocket handler should also write each `gpu_state` frame into `krelix:gpu_state:<gpu_resource_id>` with TTL ~60s. Update T030/T025 if not already done — note in completion summary.

## Acceptance Criteria

- [ ] `GET /api/v1/fit-predictions` returns one of three predictions with full `basis`.
- [ ] Agent offline → 409 `agent_not_connected`.
- [ ] Model not on HF → 404 `model_not_found_on_hf`.
- [ ] Endpoint not found → 404 `endpoint_not_found`.
- [ ] Heuristic produces correct predictions on hand-picked test cases (e.g., 8B model in FP16 → ~16GB working set, fits on A4000 16GB → `needs_offload` due to 1.25x overhead; fits comfortably on A5000 24GB; won't fit on A2000 6GB).
- [ ] `basis` JSONB contains: `model_estimated_size_mb`, `working_set_mb`, `overhead_factor`, `endpoint_total_vram_mb`, `endpoint_free_vram_mb`, `largest_single_gpu_free_vram_mb`, per-GPU breakdown.

## Out of Scope

- Persisting predictions — handled by T035 (deployment record snapshots the prediction).
- The 20-combo test set evaluation — T058.
- Improving the heuristic past the initial table-driven version — done empirically during the build.

## Notes

- The 1.25x overhead factor is a starting point. The T058 measurement will tell us if it needs tuning. Don't optimize prematurely.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
