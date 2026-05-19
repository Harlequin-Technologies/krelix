# T055 — Systemd unit + bare-metal install runbook

**Status:** Not started
**Phase:** 12 — Bare-metal/systemd host agent path
**Estimated session length:** 2 hr
**Depends on:** T054
**Blocks:** T056
**Maps to:** `deployment.md` "Bare-Metal Install Path — Host Agent" + `auth-and-security.md` systemd hardening.

---

## Objective

Ship the `krelix-agent.service` systemd unit with proper hardening, plus a documented bare-metal install runbook the operator (and other adopters) can follow.

## Files to create

- `packaging/systemd/krelix-agent.service`
- `packaging/systemd/krelix-agent.env.example`
- `docs/install/host-agent-bare-metal.md`

## Steps

1. `krelix-agent.service`:
   ```ini
   [Unit]
   Description=Krelix host agent
   After=network-online.target
   Wants=network-online.target

   [Service]
   Type=simple
   User=krelix-agent
   Group=krelix-agent
   EnvironmentFile=/etc/krelix/agent.env
   ExecStart=/opt/krelix/agent/.venv/bin/krelix-agent run
   Restart=on-failure
   RestartSec=5
   # Hardening
   NoNewPrivileges=yes
   ProtectSystem=strict
   ProtectHome=yes
   PrivateTmp=yes
   ReadWritePaths=/var/lib/krelix/hot /mnt/krelix-vault
   CapabilityBoundingSet=
   AmbientCapabilities=

   [Install]
   WantedBy=multi-user.target
   ```
2. `krelix-agent.env.example` — mirror what the install instructions in T023 show for systemd mode.
3. `docs/install/host-agent-bare-metal.md` — step-by-step:
   - Create `krelix-agent` system user, add to `video` group (or `render` — call out the choice).
   - Install Python 3.12, `uv`.
   - `git clone` repo to `/opt/krelix/agent`, `uv venv && uv pip install -e ./agent`.
   - Install vLLM into its own venv at `/opt/krelix/engines/vllm`.
   - Create `/etc/krelix/agent.env` from the example.
   - Install the systemd unit.
   - `systemctl daemon-reload && systemctl enable --now krelix-agent`.
   - Verify with `systemctl status krelix-agent` and `journalctl -u krelix-agent -f`.
   - Tear-down section: stop service, remove user, clean paths.

## Acceptance Criteria

- [ ] `krelix-agent.service` exists and successfully runs the agent on a test Debian/Ubuntu VM.
- [ ] Hardening directives are present and effective (verify with `systemd-analyze security krelix-agent`).
- [ ] Bare-metal install runbook is complete enough that a separate operator could follow it without external help.
- [ ] Logs appear in `journalctl -u krelix-agent`.

## Out of Scope

- Distro-specific packaging (deb, rpm) — backlog.
- An installer script — operators copy/paste from the runbook; if needed, a tiny `install.sh` could be added in T056.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
