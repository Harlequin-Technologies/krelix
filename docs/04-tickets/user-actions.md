# User-Required Actions — Krelix

Things only the operator can do. AI coding agents cannot perform these — they involve identity, money, network configuration, hardware setup, or external accounts. Each item lists what's needed, **when** in the build sequence it's needed, and **how** to provide it to the agents.

Consolidated from [`../03-technical/deployment.md`](../03-technical/deployment.md) and [`../03-technical/tech-plan.md`](../03-technical/tech-plan.md) Section 7. No new actions are invented here — only enumerated.

---

## Before Build Starts (do these first)

- [ ] **Confirm the GitHub repo exists** at `github.com/Harlequin-Technologies/krelix` and the operator has push access.
- [ ] **Confirm GHCR access** — pushing to `ghcr.io/harlequin-technologies/krelix-*` requires the GitHub repo's `packages: write` permission for the GITHUB_TOKEN, which is default for Actions in the same org. Verify on first CI run.

## Before Phase 1 (project scaffolding)

- [ ] **Decide on the control-plane VM** (default: a fresh Debian/Ubuntu LTS VM on `dell-proxmox.dropthe8.com`). Provision it: 8 GB+ RAM, 40 GB+ disk, Docker + Compose plugin installed.
- [ ] **Set up internal DNS** so the control-plane VM has a stable hostname (e.g., `krelix.dropthe8.com`). The agents will need to reach this address.

## Before Phase 2 (database + auth)

- [ ] **Generate `KRELIX_SECRET_KEY`** — at least 32 random bytes, base64url-encoded. Example: `python -c 'import secrets; print(secrets.token_urlsafe(32))'`. Store the value in your password manager — **losing this means losing the encrypted HF token**.
- [ ] **Generate `POSTGRES_PASSWORD`** for the compose stack. Strong random password; store in password manager.
- [ ] **Generate `REDIS_PASSWORD`** for the compose stack. Same.

## Before Phase 5 (host agent skeleton, container mode)

- [ ] **For each GPU host you intend to register:**
  - [ ] Verify GPU passthrough works at the Proxmox level (`nvidia-smi` on the Docker host VM reports all expected GPUs).
  - [ ] Install the NVIDIA Container Toolkit on the Docker host VM; verify `docker run --rm --gpus all nvidia/cuda:12.6.0-base nvidia-smi` succeeds.
  - [ ] Create the hot-tier directory (default `/var/lib/krelix/hot`) with sufficient NVMe space (50 GB+ recommended) and correct ownership.
  - [ ] If using a shared vault: pre-mount the vault filesystem at the agreed mount path (default `/mnt/krelix-vault`). Krelix does not manage NFS mounts.

## Before Phase 6 (HF browsing + fit prediction)

- [ ] **Obtain a HuggingFace access token** at `huggingface.co/settings/tokens`. Read access is sufficient for v1.
  - For any **gated models** you intend to test against (e.g., specific Llama / Gemma variants), accept the model's gating terms on the HuggingFace website under the operator's HF account.
  - You'll paste the token into the Krelix UI after first admin login — not into any agent config.

## Before Phase 10 (two-tier storage + eviction)

- [ ] **Decide hot-tier and vault paths for each registered endpoint.** Defaults are usable (`/var/lib/krelix/hot`, `/mnt/krelix-vault`), but if your fleet has heterogeneous mount points, set per-endpoint overrides via the Krelix UI.
- [ ] **Decide eviction policy and threshold** — `percent_free` vs. `absolute_free` and the numeric threshold. Default of 15% free works for most cases.

## Before Phase 12 (bare-metal host agent path, if using)

- [ ] **For each bare-metal-mode GPU host:**
  - [ ] Install Python 3.12 and `uv` system-wide or per-user.
  - [ ] Create a dedicated venv for vLLM (e.g., `/opt/krelix/engines/vllm/`) and install a pinned vLLM version: `uv pip install vllm==<version>` inside that venv. Record the Python executable path for the agent config.
  - [ ] Create the `krelix-agent` system user (no login shell) and add it to the `video` or `render` group (whichever your driver uses).
  - [ ] Grant the `krelix-agent` user ownership of the hot-tier and vault paths.

## Before Phase 13 (release prep)

- [ ] **Define the hand-curated 20-combo fit-prediction test set.** Pick 20 (model, endpoint) tuples spanning fits-comfortably / needs-offload / wont-fit outcomes. This is the basis for measuring success criterion #3 (≥ 90% prediction accuracy).
- [ ] **Run the MVD demo** (`Qwen2.5-14B-Instruct-AWQ` on the RTX A4000) end-to-end and record the wall-clock time.
- [ ] **Take a Postgres backup before tagging v1.0.0** so the v1 state is preserved if anything goes wrong post-release.

---

## Ongoing operator decisions (during normal use, not build)

These are listed for completeness but are not gating any ticket:

- **Enter the HuggingFace token** via the UI after first login.
- **Accept HF per-model gate approvals** on huggingface.co as new gated models become interesting.
- **Pin models** in the UI when you want them protected from auto-eviction.
- **Configure MIG profiles externally** via `nvidia-smi mig -i <idx> -cgi <profile>` if you want to slice a MIG-capable GPU. Krelix detects what's configured but does not change profiles in v1.
- **(Optional) Put your existing nginx-proxy-manager** in front of Krelix for TLS.

---

## What agents will need from you mid-build

Some tickets will surface a question that only you can answer. Common patterns:

- **"This dependency has a new major version — should I pin to the old one or take the upgrade?"** → Operator's call.
- **"The failure-mode catalog doesn't cover this real failure I encountered. Add it?"** → Operator's call (and worth a new ticket).
- **"Migration `XYZ` would drop a column with data — confirm?"** → Operator's call. Always back up Postgres first.

When an agent stops mid-ticket with a question, answer it before they proceed. Don't tell the agent "use your judgment" on these — that's how scope creep starts.
