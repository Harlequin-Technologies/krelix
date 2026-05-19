# T058 — Hand-curated 20-combo fit-prediction test set + measurement

**Status:** Not started
**Phase:** 13 — Release prep
**Estimated session length:** 4 hr (heavy operator time — actual deploys on the homelab)
**Depends on:** T033, T040
**Blocks:** T060
**Maps to:** Success criterion #3 (≥90% fit-prediction accuracy on a hand-curated set of ~20 combinations).

---

## Objective

Define and run the operator-driven 20-combination test set that proves fit prediction meets the ≥90% accuracy target. Output is a checked-in CSV/JSON of (model, endpoint, predicted, observed, agreement) plus a written one-page analysis. Tune the heuristic's overhead factor in T033 if accuracy is low.

## Files to create

- `docs/quality/fit-prediction-test-set.md` — definition + results table
- `docs/quality/fit-prediction-results.csv` — raw data
- `scripts/run-fit-prediction-test.py` — automation helper: given a list of (model_ref, endpoint_id), iterates: call GET /fit-predictions, then POST /deployments, wait for terminal state, record predicted vs. observed

## Steps (mostly operator-driven)

1. Operator defines the 20 combinations. Mix:
   - 7 expected `fits_comfortably` (small models on big GPUs).
   - 7 expected `needs_offload` (medium models on small GPUs / multi-GPU).
   - 6 expected `wont_fit` (huge models on small GPUs).
   - Include MIG instances if MIG profiles are configured.
2. Operator runs `scripts/run-fit-prediction-test.py` which iterates through the list, calling fit-prediction first then attempting the actual deploy with a short retry budget (1 attempt — we want raw fit-vs-reality, not "Krelix fights through to a working config").
3. Each deploy that reaches `running` → observed = `fit`. Each deploy that needed offload (vLLM auto-CPU-offload kicked in — detectable from logs) → observed = `needed_offload`. Each deploy that fails with OOM → observed = `wont_fit`.
4. Compute agreement (predicted == observed). If < 90%, tune `OVERHEAD_FACTOR` in T033's logic and re-run.
5. Write the one-page analysis.

## Acceptance Criteria

- [ ] 20 combinations defined, covering all three predicted outcomes.
- [ ] Test set runs end-to-end via the automation script.
- [ ] Agreement ≥ 90% across the 20 combinations.
- [ ] CSV is checked in.
- [ ] One-page analysis written: what worked, what surprised us, what we tuned.

## Out of Scope

- Adding the test set to CI — it requires real GPUs, can't run in CI in v1.
- Expanding beyond 20 — operator can grow the set post-v1 as more models are tried.

## Notes

- This is the operator's primary v1-shipping quality gate for fit prediction. Don't skip it.
- If accuracy is stuck < 90% even after tuning, the heuristic may need fundamental rework (e.g., model-card-driven memory estimation). That'd be a follow-up ticket, not a v1 blocker — but document the gap honestly.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
