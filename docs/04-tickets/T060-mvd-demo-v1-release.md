# T060 — MVD demo run + v1.0.0 release tag

**Status:** Not started
**Phase:** 13 — Release prep
**Estimated session length:** 2 hr (mostly operator-driven)
**Depends on:** T057, T058, T059
**Blocks:** None — this is the final ticket.
**Maps to:** Success criteria #1, #4, #5, #6 (MVD demo passes, time-to-endpoint ≤30 min, zero-terminal, vLLM working).

---

## Objective

Run the canonical MVD demo end-to-end on the operator's homelab, capture the wall-clock timing, verify all v1 success criteria pass, then tag `v1.0.0`. This is the release.

## Files to create

- `docs/quality/mvd-demo-run.md` — written record of the demo run: date, environment, wall-clock from click-deploy to URL-responding-to-curl, screenshots/logs, anything notable

## Files to modify

- `CHANGELOG.md` — finalize v1.0.0 entry with the actual capabilities shipped
- `pyproject.toml`/`package.json` — bump version to `1.0.0`

## Steps (mostly operator-driven)

1. Confirm the homelab is in a clean state: control plane running, at least the epyc-proxmox endpoint registered, RTX A4000 visible.
2. Operator logs in to Krelix UI fresh.
3. Browses HF for `Qwen/Qwen2.5-14B-Instruct-AWQ`; views fit prediction against A4000 → `fits_comfortably`.
4. Click Deploy → select A4000 → submit. Start stopwatch.
5. Watch the live status transitions in the UI. Stopwatch stops when `running` appears and a `curl` to the inference URL returns a valid completion.
6. Record wall-clock. Should be ≤ 30 minutes per success criterion #1.
7. Verify in passing: no terminal sessions were opened on the GPU host during the deploy (success criterion #4).
8. Tear down: stop the deployment from the UI; verify clean shutdown.
9. Run through the seven success criteria from `success-metrics.md` and check each off in `docs/quality/mvd-demo-run.md`.
10. Update CHANGELOG with final v1.0.0 entry. Bump versions.
11. Tag `v1.0.0` and push; verify the release workflow (T059) publishes `:1.0.0` + `:latest` images.

## Acceptance Criteria

- [ ] MVD demo completes in ≤ 30 minutes on the canonical hardware (Qwen2.5-14B-Instruct-AWQ on RTX A4000 via vLLM).
- [ ] No ssh sessions were opened on the GPU host during the deploy.
- [ ] All seven success criteria from `success-metrics.md` are checked off in writing.
- [ ] `v1.0.0` tag is created and pushed; release workflow produces tagged images.
- [ ] `docs/quality/mvd-demo-run.md` is written and committed.
- [ ] CHANGELOG.md is final.

## Out of Scope

- Marketing announcement — "quietly public," no need.
- Adoption metrics tracking — backlog.

## Notes

- If the MVD demo exceeds 30 min, the most likely culprit is download bandwidth, not Krelix. Document this honestly and consider whether to count it against success criterion #1 (suggested: count agent-internal time separately from network-bound download time).
- This ticket can be re-run if a "v1.0.1" or "v1.1.0" follows shortly. The MVD demo run doc is timestamped.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
