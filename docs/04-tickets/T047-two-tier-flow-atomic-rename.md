# T047 — Two-tier flow: download → hot → background copy to vault; vault → hot on reuse; atomic rename

**Status:** Not started
**Phase:** 10 — Two-tier storage + eviction
**Estimated session length:** 3 hr
**Depends on:** T037
**Blocks:** T048
**Maps to:** `architecture.md` "Two-Tier Model Storage" + "Deployment flow (model storage)".

---

## Objective

Augment the agent's deploy path (T037) with the full two-tier flow: check hot → if missing, check vault → if missing, download from HF. After a fresh HF download, kick off a background copy from hot to vault. Use `.partial`-suffix + atomic rename for crash safety. Report `artifact_state` frames to the control plane so the `model_artifact` DB rows track tier presence.

## Files to create

- `agent/src/krelix_agent/two_tier.py` — `resolve_artifact_location(model_ref, revision)` returns `(location, source)` where source ∈ {hot, vault, download}
- `agent/src/krelix_agent/copy_jobs.py` — `copy_hot_to_vault(src, dst)` with atomic rename, runs in `asyncio.to_thread`
- `agent/tests/test_two_tier.py`

## Files to modify

- `agent/src/krelix_agent/commands/deploy.py` — wrap the existing download with the two-tier resolution
- `backend/src/krelix/api/agent/v1/stream.py` — handle `artifact_state` frames from the agent (upsert `model_artifact` rows)

## Steps

1. `two_tier.py`:
   - `resolve_artifact_location(hot_root, vault_root, model_ref, revision) -> (path, source)`:
     - If hot path exists (and `download_completed` marker present): return (hot_path, "hot").
     - Else if vault path exists: return (vault_path, "vault") — caller will copy to hot.
     - Else: return (hot_path, "download") — caller will download from HF.
2. `copy_jobs.py`:
   - `copy_hot_to_vault(src, dst)`: write to `dst.partial` (sibling), `os.fsync`, then `os.rename` to `dst`. On crash mid-write, the partial is left behind; on next agent start, a `cleanup_partials` sweep at the relevant tier removes stale `.partial` files older than 5 min.
   - Same atomic-rename pattern for vault → hot copies (used when reusing a vault model).
3. In `commands/deploy.py`:
   - Before downloading: call `resolve_artifact_location`.
   - If source=`hot`: skip download, proceed to engine.start().
   - If source=`vault`: copy vault → hot via `copy_jobs`, send progress frames (`status: copying`), then proceed.
   - If source=`download`: download → hot (existing logic), then spawn a background task `copy_hot_to_vault` (don't await — it shouldn't block deployment success).
4. After every operation that changes tier presence, send an `artifact_state` frame to the control plane: `{model_ref, resolved_revision, in_hot_tier, in_vault_tier, hot_tier_size_bytes, vault_tier_size_bytes}`. Set `last_used_at = now()` when the artifact is consumed by an engine.start().
5. Control plane handles `artifact_state` frames: upsert `model_artifact` row keyed by `(endpoint_id, model_id, resolved_revision)`.
6. Add a `cleanup_partials` task that runs on agent startup: walks hot + vault, removes `.partial` files older than 5 min.

## Acceptance Criteria

- [ ] Fresh deploy of model X: status goes `pending → provisioning → downloading → starting → running`; background vault copy completes after deployment is live.
- [ ] Second deploy of model X (now in vault) to same endpoint after eject: status goes `pending → provisioning → copying → starting → running` (no `downloading` step).
- [ ] Third deploy when model X is still in hot tier: skips both copy and download; status straight to `starting`.
- [ ] Crash during HF download leaves a `.partial` file; agent restart cleans it up.
- [ ] Crash during hot→vault copy leaves a `.partial` file at vault; cleaned up; the hot copy remains intact so the model is still usable.
- [ ] `model_artifact` DB rows correctly reflect in_hot / in_vault tier flags.
- [ ] `last_used_at` is updated on every engine.start() that consumes the artifact.

## Out of Scope

- LRU eviction — T048.
- Pinning — T049.
- Multi-host vault concurrency (two hosts copying same model to a shared vault simultaneously) — for v1, the rename-when-done pattern makes this safe-ish; a tighter solution (file lock) is a v1.x concern.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
