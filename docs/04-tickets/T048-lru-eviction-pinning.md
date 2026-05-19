# T048 — LRU eviction sweep with pinning support

**Status:** Not started
**Phase:** 10 — Two-tier storage + eviction
**Estimated session length:** 2.5 hr
**Depends on:** T047
**Blocks:** T049
**Maps to:** `architecture.md` "Eviction flow (hot tier)"; US-M-09 (eject) and the auto-eviction policy.

---

## Objective

Implement the LRU sweep on the agent: periodically (and on threshold-trigger after large writes), evaluate the configured eviction policy. List non-pinned, non-active hot-tier artifacts sorted by `last_used_at` ascending; delete oldest first until free space meets threshold. Emit `eviction_event` frames so the control plane records what was evicted.

## Files to create

- `agent/src/krelix_agent/eviction.py` — `sweep_hot_tier(resolved_config)` + `disk_usage_for(path)`
- `agent/tests/test_eviction.py`

## Files to modify

- `agent/src/krelix_agent/commands/deploy.py` — after a successful download/copy that consumes meaningful disk, call `sweep_hot_tier`
- Add a periodic sweep task to the agent's main loop (every 5 min)
- `backend/src/krelix/api/agent/v1/stream.py` — handle `eviction_event` frames (write `deployment_event` with `event_type=eviction_triggered` linked to the affected artifact)

## Steps

1. `eviction.py`:
   ```python
   async def sweep_hot_tier(*, hot_path, policy_type, threshold, active_artifacts, pinned_artifacts, all_artifacts):
       """
       active_artifacts: set of artifact_ids currently in use by running engines
       pinned_artifacts: set of artifact_ids marked pinned
       all_artifacts: list of {artifact_id, hot_path, last_used_at, size_bytes}
       """
       free_now = free_bytes(hot_path)
       total = total_bytes(hot_path)
       if policy_type == "percent_free":
           target_free = total * (threshold / 100)
       else:  # absolute_free
           target_free = threshold  # bytes
       if free_now >= target_free:
           return []  # nothing to do
       evictable = [a for a in all_artifacts
                    if a["artifact_id"] not in active_artifacts
                    and a["artifact_id"] not in pinned_artifacts]
       evictable.sort(key=lambda a: a["last_used_at"] or datetime.min)
       evicted = []
       for a in evictable:
           if free_bytes(hot_path) >= target_free:
               break
           shutil.rmtree(a["hot_path"])
           evicted.append(a)
       return evicted
   ```
2. Wire up: the agent's state already tracks which artifacts are currently loaded by engines (from `running` deployments). Active set = those artifact_ids. Pinned set = artifacts the control plane has flagged via a `pin_artifact` command (T049).
3. For each evicted artifact, send an `eviction_event` frame to the control plane.
4. Control plane on `eviction_event`: write a `deployment_event(event_type=eviction_triggered, payload={artifact_id, reason, freed_bytes})` linked to the most-recent deployment that used that artifact (best-effort; payload also stands alone).
5. Add a periodic sweep task to the agent's `run` command (every 5 min).

## Acceptance Criteria

- [ ] Eviction policy is read from resolved config (per-endpoint or global).
- [ ] Eviction respects both pinned and active filters.
- [ ] Oldest-by-`last_used_at` is evicted first.
- [ ] Eviction stops as soon as the threshold is satisfied.
- [ ] `eviction_event` frames are sent + recorded as `deployment_event` rows.
- [ ] Periodic sweep runs every 5 min; also triggered after each download/copy that wrote >1 GB.

## Out of Scope

- Pin/unpin from the UI — T049.
- Vault tier eviction — not in v1 (vault is meant to be larger and operator-managed).
- Eviction analytics — backlog.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
