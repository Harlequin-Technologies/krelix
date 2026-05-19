# T042 — Auto-iteration: retry budget, log capture during start, config adjustment loop

**Status:** Not started
**Phase:** 8 — Auto-iteration loop
**Estimated session length:** 3 hr
**Depends on:** T037, T041
**Blocks:** T043
**Maps to:** US-M-05 "Krelix automatically adjusts configuration and retries within a bounded number of attempts."

---

## Objective

Wrap the deploy flow in T037 with an auto-iteration loop: capture the vLLM startup logs into an in-memory buffer; if startup fails, run the buffer through `find_matching_failure`; if a match exists and the retry budget isn't exhausted, apply the config adjustment and retry. On exhaustion, send `failed` status with the final logs as `failure_reason`.

## Files to modify

- `agent/src/krelix_agent/commands/deploy.py` — extract the start logic into an iterating wrapper

## Files to create

- `agent/src/krelix_agent/iteration/orchestrator.py` — the loop
- `agent/tests/test_auto_iteration.py` — table-driven: given a sequence of "fake vLLM that fails with log X on attempt N", verify the loop applies the right adjustments and converges (or exhausts)

## Steps

1. `iteration/orchestrator.py`:
   ```python
   async def deploy_with_iteration(
       *, deployment_id, model_path, gpu_indices, initial_config,
       retry_budget, engine: EngineAdapter, send_status, log_capture,
   ) -> StartResult:
       config = initial_config
       attempt = 0
       last_logs = ""
       while attempt <= retry_budget:
           attempt += 1
           await send_status({"status": "starting", "iteration": {"attempt": attempt}})
           try:
               result = await engine.start(deployment_id, model_path, gpu_indices, config)
               # Wait for health-ready; if it never becomes ready, raise.
               await wait_until_ready(result.inference_url, timeout=300)
               await send_status({"status": "running", ...result.dict()})
               return result
           except Exception as e:
               last_logs = await log_capture.snapshot()
               failure = find_matching_failure(last_logs, e)
               if failure is None or attempt > retry_budget:
                   await send_status({"status": "failed", "failure_reason": ..., "logs": last_logs[-2000:]})
                   raise
               # Adjusted config for next attempt
               new_config = failure.apply(config, {"attempt": attempt})
               if new_config.get("_needs_redownload"):
                   # Phase 8 doesn't handle re-download; mark as terminal failure
                   await send_status({"status": "failed", "failure_reason": "tokenizer_missing_redownload_required"})
                   raise
               await send_status({
                   "status": "starting",
                   "iteration": {
                       "attempt": attempt + 1, "reason": failure.name,
                       "adjusted_args": diff(config, new_config),
                   },
               })
               config = new_config
               # Tear down the failed container before retrying
               await engine.stop(result.engine_handle) if "result" in locals() else None
       # exhausted
       await send_status({"status": "failed", "failure_reason": "iteration_budget_exhausted", "logs": last_logs[-2000:]})
       raise IterationExhausted()
   ```
2. `commands/deploy.py` — replace the single-attempt start with `await deploy_with_iteration(...)`.
3. Log capture: a tiny in-memory rolling buffer (LogCapture class) that subscribes to the vLLM container's stdout/stderr. Returns `snapshot()` as a string. (This is also the foundation for log streaming in T044.)

## Acceptance Criteria

- [ ] Iteration loop respects `retry_budget` from the resolved config.
- [ ] Each iteration reports `starting` with iteration metadata before the attempt.
- [ ] On match: config is adjusted per `FailureMode.apply` and retried.
- [ ] On no match or exhausted: `failed` with the last log tail + reason.
- [ ] `_needs_redownload` signal terminates iteration with a specific failure reason (re-download is v2+).
- [ ] Test: simulate vLLM failing twice (OOM at load → reduce gpu_memory_utilization → success) → expects 2 iterations with the correct config change.

## Out of Scope

- Reporting iteration events to the control plane via WS frames — T043.
- Re-downloading on `_needs_redownload` — v2 concern.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
