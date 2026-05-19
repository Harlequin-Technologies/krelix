# T041 — Failure-mode catalog + recovery strategies (agent side)

**Status:** Not started
**Phase:** 8 — Auto-iteration loop
**Estimated session length:** 2.5 hr
**Depends on:** T037
**Blocks:** T042
**Maps to:** Tech-plan open question "Auto-iteration failure-mode catalog"; success criterion #1 (time-to-endpoint ≤ 30 min).

---

## Objective

Define a structured catalog of known vLLM failure modes and the corresponding config adjustments. Built as a small, testable module — each entry has a name, a log-pattern matcher (regex or substring), and a `apply(current_config) -> new_config` function. The catalog starts with the minimum set from the tech plan and is designed to grow as real failures are encountered.

## Files to create

- `agent/src/krelix_agent/iteration/__init__.py` — empty
- `agent/src/krelix_agent/iteration/catalog.py` — failure-mode entries
- `agent/src/krelix_agent/iteration/matcher.py` — `find_matching_failure(log_lines, exception) -> FailureMode | None`
- `agent/tests/test_failure_catalog.py` — table-driven tests, one case per entry

## Steps

1. `catalog.py` — module-level list of `FailureMode` entries. Each:
   ```python
   @dataclass
   class FailureMode:
       name: str
       description: str
       matches: Callable[[str, Exception | None], bool]
       apply: Callable[[dict, dict], dict]  # (current_config, context) -> adjusted_config

   FAILURES = [
       FailureMode(
           name="oom_at_load",
           description="CUDA OOM during model load. Reduce gpu_memory_utilization.",
           matches=lambda logs, exc: "CUDA out of memory" in logs and "loading" in logs.lower(),
           apply=lambda cfg, ctx: {**cfg, "gpu_memory_utilization": max(0.7, cfg.get("gpu_memory_utilization", 0.9) - 0.1)},
       ),
       FailureMode(
           name="oom_at_first_inference",
           description="CUDA OOM after model loaded. Reduce max_model_len.",
           matches=lambda logs, exc: "CUDA out of memory" in logs and "loaded" in logs.lower(),
           apply=lambda cfg, ctx: {**cfg, "max_model_len": max(2048, cfg.get("max_model_len", 8192) // 2)},
       ),
       FailureMode(
           name="kv_cache_too_small",
           description="KV cache cannot hold max_model_len. Reduce max_model_len.",
           matches=lambda logs, exc: "KV cache" in logs and ("not enough" in logs.lower() or "too small" in logs.lower()),
           apply=lambda cfg, ctx: {**cfg, "max_model_len": max(2048, cfg.get("max_model_len", 8192) // 2)},
       ),
       FailureMode(
           name="unrecognized_quantization_flag",
           description="vLLM doesn't recognize the quantization spec. Drop the flag and let vLLM detect.",
           matches=lambda logs, exc: "unsupported quantization" in logs.lower() or "unknown quantization" in logs.lower(),
           apply=lambda cfg, ctx: {k: v for k, v in cfg.items() if k != "quantization"},
       ),
       FailureMode(
           name="missing_tokenizer_revision",
           description="Tokenizer files missing for the requested revision. Retry with default revision (this requires re-download — flag it).",
           matches=lambda logs, exc: "tokenizer" in logs.lower() and ("not found" in logs.lower() or "missing" in logs.lower()),
           apply=lambda cfg, ctx: {**cfg, "_needs_redownload": True},  # signal to outer loop
       ),
   ]
   ```
2. `matcher.py` — `find_matching_failure(logs, exception) -> FailureMode | None` walks the catalog and returns the first match. If multiple could match, prefer the most specific (longer description / more specific log pattern).

## Acceptance Criteria

- [ ] All five minimum-set entries from the tech plan are implemented.
- [ ] Each entry has a unit test verifying the matcher and the apply function.
- [ ] Apply functions are pure — they return a new config dict, don't mutate the input.
- [ ] The catalog is a simple module-level list — easy to add entries in future tickets / by the operator.

## Out of Scope

- Wiring into the deploy flow — T042.
- ML/automatic catalog expansion — explicitly v2+.
- Telemetry on which entries fire most often — could be a follow-up.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
