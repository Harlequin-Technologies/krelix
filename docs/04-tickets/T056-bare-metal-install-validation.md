# T056 — Bare-metal install validation on a real Debian/Ubuntu VM

**Status:** Not started
**Phase:** 12 — Bare-metal/systemd host agent path
**Estimated session length:** 2 hr (mostly operator-driven)
**Depends on:** T055
**Blocks:** Release readiness
**Maps to:** Acceptance for the dual-mode commitment (deployment.md "two paths first-class").

---

## Objective

Validate the bare-metal install path end-to-end on a fresh Debian/Ubuntu VM that the operator provisions. This is partly an operator action (provisioning the VM, having a GPU passed through) and partly an agent-side validation that the systemd unit launches a successful deploy.

## Files to modify

- `docs/install/host-agent-bare-metal.md` — fix any gaps discovered during this validation
- `packaging/systemd/krelix-agent.service` — fix hardening issues if any

## Files to create

- None (this is a validation ticket — the artifacts are install-runbook clarifications)

## Steps (mostly manual)

1. Operator provisions a fresh Debian-12 or Ubuntu-24.04 VM with a single GPU passed through.
2. Operator follows `docs/install/host-agent-bare-metal.md` step-by-step.
3. Register the host as an endpoint via the Krelix UI; paste token into `/etc/krelix/agent.env`.
4. Start the service; verify it connects (endpoint shows `online` in UI, GPUs reported).
5. Trigger a deploy of `Qwen2.5-14B-Instruct-AWQ` (or smaller if the VM's GPU can't hold it).
6. Verify the vLLM subprocess starts, becomes ready, serves inferences.
7. Verify logs stream to the UI.
8. Stop the deployment from the UI; verify the subprocess is reaped.
9. Restart the service (`systemctl restart krelix-agent`); verify reconnection without re-registration.
10. Capture any friction in install steps; update the runbook accordingly.

## Acceptance Criteria

- [ ] A fresh VM can be brought to "Krelix endpoint registered and operational" by following only `docs/install/host-agent-bare-metal.md`.
- [ ] A test deploy succeeds end-to-end (download → start → running → stop) in systemd mode.
- [ ] Logs appear in the UI live during the deploy.
- [ ] Service restart preserves the agent's connection state (re-registration is idempotent).
- [ ] `systemd-analyze security krelix-agent` reports a low / medium score — not "UNSAFE."

## Out of Scope

- Validating systemd mode on non-Debian/Ubuntu distros — backlog (Fedora, Arch can follow analogous steps but not v1-validated).
- Validating multiple bare-metal agents on the same control plane — covered by the broader v1 test if the operator has the hardware.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
