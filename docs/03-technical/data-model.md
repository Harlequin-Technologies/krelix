# Data Model — Krelix

All persistent entity state lives in **PostgreSQL 18**. Schema is owned and migrated by Alembic. Field names use `snake_case`; primary keys are `UUID` (Postgres `uuid` type, generated with `uuid_generate_v4()` or app-side via Python `uuid4()`) unless noted otherwise.

Common conventions (apply to every table unless noted):

- `id UUID PRIMARY KEY DEFAULT uuid_generate_v4()`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()` (touched by ORM event listener)
- Soft-deletable tables have `deleted_at TIMESTAMPTZ NULL`; queries default to `deleted_at IS NULL`.

JSONB is used liberally for flexible blobs (engine configs, basis metadata, HF metadata caches) — we lean Postgres for entity truth, JSONB for shape we'd otherwise over-normalize.

---

## Entities

### `admin_user`

**Purpose:** Single-operator authentication. v1 has exactly one row; the table is shaped to support multiple users in the eventual commercial product.

| Name | Type | Constraints | Notes |
|------|------|-------------|-------|
| id | UUID PRIMARY KEY | NOT NULL | |
| username | TEXT | NOT NULL, UNIQUE | login name |
| password_hash | TEXT | NOT NULL | Argon2id hash (via `pwdlib`) — format string includes algorithm + parameters for `verify_and_update` transparent upgrades |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| last_login_at | TIMESTAMPTZ | NULL | |

**Indexes:** UNIQUE on `username`.

---

### `agent_registration_token`

**Purpose:** Authenticates host agents to the control plane. Each Endpoint has exactly one associated token. The token is generated when the operator initiates endpoint registration (before the host agent is installed); the operator pastes the token into the host agent's config when installing it. Once an agent has connected with the token, the token rotates / refreshes per a documented lifecycle (deferred to implementation).

| Name | Type | Constraints | Notes |
|------|------|-------------|-------|
| id | UUID PRIMARY KEY | NOT NULL | |
| token_hash | TEXT | NOT NULL, UNIQUE | sha256 of the actual token bearer string; bearer string never stored |
| label | TEXT | NOT NULL | operator-visible label, e.g., "epyc-proxmox bootstrap" |
| consumed_at | TIMESTAMPTZ | NULL | when the agent first registered with it |
| created_at | TIMESTAMPTZ | NOT NULL | |
| revoked_at | TIMESTAMPTZ | NULL | nulled when active; set when revoked |

**Indexes:** UNIQUE on `token_hash`.

---

### `vault`

**Purpose:** A named, operator-defined storage location for long-term model artifacts. Krelix references vaults by mount path; the operator owns the underlying storage (local NVMe directory, NFS export, etc.) and ensures it is mounted on the right hosts.

| Name | Type | Constraints | Notes |
|------|------|-------------|-------|
| id | UUID PRIMARY KEY | NOT NULL | |
| name | TEXT | NOT NULL, UNIQUE | operator-visible name, e.g., "primary-nfs-vault" |
| description | TEXT | NULL | free text |
| mount_path | TEXT | NOT NULL | expected absolute path on hosts assigned to this vault, e.g., `/mnt/krelix-vault` |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| deleted_at | TIMESTAMPTZ | NULL | soft delete |

**Indexes:** UNIQUE on `name`.

**Relationships:** Referenced by `endpoint.vault_id` (per-endpoint override) and by `global_settings.default_vault_id`.

---

### `global_settings`

**Purpose:** Single-row table holding system-wide defaults that endpoints can override.

| Name | Type | Constraints | Notes |
|------|------|-------------|-------|
| id | INTEGER PRIMARY KEY | NOT NULL, CHECK (id = 1) | enforced single-row |
| default_hot_tier_path | TEXT | NOT NULL | e.g., `/var/lib/krelix/hot` |
| default_vault_id | UUID | NULL REFERENCES vault(id) | NULL → no default vault (some hosts may have no vault) |
| eviction_policy_type | TEXT | NOT NULL, CHECK IN ('percent_free','absolute_free') | |
| eviction_threshold | REAL | NOT NULL | percent (0–100) if `percent_free`; bytes if `absolute_free` |
| auto_iteration_retry_budget | INTEGER | NOT NULL DEFAULT 5 | max bounded retries per deployment |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Migration:** seeded by Alembic to id=1 with sensible defaults on first startup; never deleted.

---

### `endpoint`

**Purpose:** A registered GPU host (Docker host that runs vLLM workloads). One Krelix host agent runs on each.

| Name | Type | Constraints | Notes |
|------|------|-------------|-------|
| id | UUID PRIMARY KEY | NOT NULL | |
| name | TEXT | NOT NULL, UNIQUE | machine-friendly identifier, e.g., `epyc-proxmox` |
| display_name | TEXT | NOT NULL | UI-friendly label |
| hostname | TEXT | NOT NULL | FQDN of the GPU host, e.g., `epyc-proxmox.dropthe8.com` |
| registration_token_id | UUID | NOT NULL REFERENCES agent_registration_token(id) | |
| agent_status | TEXT | NOT NULL, CHECK IN ('never_connected','online','offline') | starts at `never_connected` |
| agent_version | TEXT | NULL | reported by the agent at connect |
| agent_runtime_mode | TEXT | NULL, CHECK IN (NULL,'docker','systemd') | reported by the agent at registration; informs UI labeling and operator debugging |
| last_heartbeat_at | TIMESTAMPTZ | NULL | |
| **Override fields (NULL → fall back to global_settings):** | | | |
| hot_tier_path | TEXT | NULL | override of `default_hot_tier_path` |
| vault_id | UUID | NULL REFERENCES vault(id) | override of `default_vault_id` |
| eviction_policy_type | TEXT | NULL, CHECK IN ('percent_free','absolute_free') | |
| eviction_threshold | REAL | NULL | |
| auto_iteration_retry_budget | INTEGER | NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| deleted_at | TIMESTAMPTZ | NULL | soft delete |

**Indexes:** UNIQUE on `name`. UNIQUE on `hostname` (active rows only).

**Relationships:** has many `gpu_resource`, `model_artifact`, `deployment`.

---

### `gpu_resource`

**Purpose:** An individual GPU attached to an endpoint, as reported by the host agent via NVML.

| Name | Type | Constraints | Notes |
|------|------|-------------|-------|
| id | UUID PRIMARY KEY | NOT NULL | |
| endpoint_id | UUID | NOT NULL REFERENCES endpoint(id) ON DELETE CASCADE | |
| gpu_index | INTEGER | NOT NULL | NVML index on the host (for full GPUs) or MIG-instance index |
| nvml_uuid | TEXT | NOT NULL | stable GPU/MIG-instance identifier from NVML |
| model_name | TEXT | NOT NULL | e.g., "NVIDIA RTX A4000" |
| vram_total_mb | INTEGER | NOT NULL | total VRAM on this GPU or MIG instance |
| compute_capability | TEXT | NULL | e.g., "8.6" |
| mig_capable | BOOLEAN | NOT NULL DEFAULT FALSE | TRUE if this physical GPU supports MIG (datacenter-class hardware) |
| mig_enabled_on_parent | BOOLEAN | NOT NULL DEFAULT FALSE | TRUE if the parent physical GPU is currently in MIG mode |
| mig_profile | TEXT | NULL | e.g., `3g.36gb`; NULL means this row represents a full GPU, not a MIG instance |
| parent_nvml_uuid | TEXT | NULL | when this row IS a MIG instance, this points to the parent physical GPU's NVML UUID |
| last_reported_at | TIMESTAMPTZ | NOT NULL | when the agent last reported this GPU's stats |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** UNIQUE on `(endpoint_id, nvml_uuid)`. Index on `endpoint_id`. Index on `parent_nvml_uuid` for MIG-instance lookups.

**Note:** Live VRAM utilization (`vram_used_mb`, `gpu_util_pct`, temperature, power) is **not stored as columns** — it's reported live by the agent and either streamed to the UI directly via WebSocket or buffered in Redis. v2 (D phase) is where these become persistent time series; v1 keeps them ephemeral.

**MIG handling (v1 = detection only):**

- When a physical GPU is **not** in MIG mode, the agent reports one `gpu_resource` row representing the whole GPU. `mig_capable` reflects hardware capability; `mig_enabled_on_parent=FALSE`; `mig_profile=NULL`; `parent_nvml_uuid=NULL`.
- When a physical GPU **is** in MIG mode (operator pre-configured this externally via `nvidia-smi`), the agent reports one `gpu_resource` row **per active MIG instance**. Each MIG instance has its own NVML UUID, its own VRAM allotment, and its `parent_nvml_uuid` points to the parent physical GPU. `mig_profile` is set (e.g., `3g.36gb`). The parent physical GPU itself is **not** also reported as a separate row — only the slices are.
- v1 does **not** create, change, or destroy MIG profiles. Profile management is an operator-side `nvidia-smi` task outside Krelix. Automatic MIG profile change is deferred to v1.x / v2 (see [`tech-plan.md`](tech-plan.md) open questions).

---

### `huggingface_credential`

**Purpose:** Single-row table holding the operator's HuggingFace token.

| Name | Type | Constraints | Notes |
|------|------|-------------|-------|
| id | INTEGER PRIMARY KEY | NOT NULL, CHECK (id = 1) | enforced single-row |
| token_encrypted | BYTEA | NOT NULL | symmetric-encrypted with a key derived from a control-plane secret |
| label | TEXT | NULL | optional operator label |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Migration:** id=1 row created lazily on first save (no seed).

---

### `model`

**Purpose:** A HuggingFace model Krelix has at least seen. Acts as a metadata cache + the entity that artifacts/deployments reference.

| Name | Type | Constraints | Notes |
|------|------|-------------|-------|
| id | UUID PRIMARY KEY | NOT NULL | |
| hf_model_ref | TEXT | NOT NULL, UNIQUE | e.g., `Qwen/Qwen2.5-14B-Instruct-AWQ` |
| declared_license | TEXT | NULL | from model card metadata |
| declared_license_url | TEXT | NULL | |
| gated | BOOLEAN | NOT NULL DEFAULT FALSE | model requires HF gate approval |
| primary_format | TEXT | NULL, CHECK IN (NULL,'safetensors','gguf','pt') | dominant artifact format |
| primary_quantization | TEXT | NULL | e.g., `awq-4bit`, `gptq-4bit`, `fp16`, `bf16` |
| estimated_size_bytes | BIGINT | NULL | sum of weights file sizes per HF manifest; basis for fit prediction |
| hf_metadata | JSONB | NOT NULL DEFAULT '{}' | raw HF metadata snapshot (model card frontmatter, file manifest, etc.) |
| last_metadata_fetched_at | TIMESTAMPTZ | NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** UNIQUE on `hf_model_ref`. GIN index on `hf_metadata` for JSONB queries.

---

### `model_artifact`

**Purpose:** A concrete copy of a model at a resolved HuggingFace revision, on a specific endpoint, in one or both tiers (hot, vault). One row per (endpoint, model, revision) tuple.

| Name | Type | Constraints | Notes |
|------|------|-------------|-------|
| id | UUID PRIMARY KEY | NOT NULL | |
| model_id | UUID | NOT NULL REFERENCES model(id) | |
| endpoint_id | UUID | NOT NULL REFERENCES endpoint(id) ON DELETE CASCADE | |
| resolved_revision | TEXT | NOT NULL | HF commit hash / snapshot reference (immutable) |
| in_hot_tier | BOOLEAN | NOT NULL DEFAULT FALSE | |
| in_vault_tier | BOOLEAN | NOT NULL DEFAULT FALSE | |
| hot_tier_size_bytes | BIGINT | NULL | NULL when not in hot |
| vault_tier_size_bytes | BIGINT | NULL | NULL when not in vault |
| pinned | BOOLEAN | NOT NULL DEFAULT FALSE | pinned models survive auto-eviction |
| last_used_at | TIMESTAMPTZ | NULL | updated by the agent when vLLM loads this artifact; basis for LRU eviction |
| download_completed_at | TIMESTAMPTZ | NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| deleted_at | TIMESTAMPTZ | NULL | soft delete (artifact fully removed from both tiers) |

**Indexes:** UNIQUE on `(endpoint_id, model_id, resolved_revision)`. Index on `(endpoint_id, last_used_at)` for LRU sweeps. Index on `(endpoint_id, in_hot_tier)`.

---

### `deployment`

**Purpose:** A vLLM container instance running (or attempted to be running) a specific model artifact on a specific endpoint.

| Name | Type | Constraints | Notes |
|------|------|-------------|-------|
| id | UUID PRIMARY KEY | NOT NULL | |
| endpoint_id | UUID | NOT NULL REFERENCES endpoint(id) | |
| model_id | UUID | NOT NULL REFERENCES model(id) | |
| model_artifact_id | UUID | NULL REFERENCES model_artifact(id) | NULL during `pending` / `downloading`; set once an artifact exists |
| resolved_revision | TEXT | NOT NULL | duplicated from artifact for immutability |
| status | TEXT | NOT NULL, CHECK IN ('pending','provisioning','downloading','copying','starting','running','stopped','failed') | |
| engine | TEXT | NOT NULL DEFAULT 'vllm' | v1: always `vllm` |
| engine_version | TEXT | NULL | vLLM version reported by the running container |
| gpu_indices | INTEGER[] | NOT NULL DEFAULT '{}' | which GPUs on the endpoint are in use |
| initial_config | JSONB | NOT NULL | engine launch args Krelix picked initially |
| final_config | JSONB | NULL | the config the deployment ended up with after auto-iteration; NULL until terminal status |
| iteration_count | INTEGER | NOT NULL DEFAULT 0 | how many auto-iteration retries occurred |
| inference_url | TEXT | NULL | OpenAI-compatible URL; populated when status reaches `running` |
| internal_port | INTEGER | NULL | host-side port the engine binds to |
| engine_handle | TEXT | NULL | runtime-specific handle for the engine instance — Docker container ID in container mode, PID (as string) in bare-metal mode |
| engine_runtime_mode | TEXT | NULL, CHECK IN (NULL,'docker','systemd') | which runtime executed this deployment; copied from the endpoint at deploy time for historical audit |
| fit_prediction_at_initiation | TEXT | NOT NULL, CHECK IN ('fits_comfortably','needs_offload','wont_fit') | recorded at deploy time |
| fit_prediction_basis | JSONB | NOT NULL DEFAULT '{}' | numbers that drove the prediction (model size, free VRAM, etc.) |
| observed_outcome | TEXT | NULL, CHECK IN (NULL,'fit','needed_offload','wont_fit') | set on terminal status; basis for accuracy measurement (success criterion #3) |
| failure_reason | TEXT | NULL | terminal failure summary |
| initiated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| started_at | TIMESTAMPTZ | NULL | when status reached `running` |
| stopped_at | TIMESTAMPTZ | NULL | |
| failed_at | TIMESTAMPTZ | NULL | |
| created_by_user_id | UUID | NOT NULL REFERENCES admin_user(id) | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** Index on `endpoint_id`. Index on `(endpoint_id, status)` for "what's active on each endpoint" queries. Index on `model_id`. Index on `initiated_at DESC` for the deployment-history view (US-S-03).

**Note on lifecycle:** Deployment rows are **never deleted** — they're the durable history (US-S-03). The `model_artifact` they reference can be removed (deleted_at on the artifact row), but the deployment row preserves the resolved revision, final config, and outcome for audit and accuracy measurement.

---

### `deployment_event`

**Purpose:** Append-only state-transition log for each deployment. Useful for debugging the auto-iteration loop, building the UI's live-status updates, and the audit trail.

| Name | Type | Constraints | Notes |
|------|------|-------------|-------|
| id | UUID PRIMARY KEY | NOT NULL | |
| deployment_id | UUID | NOT NULL REFERENCES deployment(id) ON DELETE CASCADE | |
| event_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| event_type | TEXT | NOT NULL | e.g., `status_changed`, `iteration_started`, `iteration_failed`, `vllm_log_excerpt`, `eviction_triggered` |
| from_status | TEXT | NULL | when `event_type=status_changed` |
| to_status | TEXT | NULL | when `event_type=status_changed` |
| message | TEXT | NULL | human-readable summary |
| payload | JSONB | NOT NULL DEFAULT '{}' | structured details |

**Indexes:** Index on `(deployment_id, event_at DESC)`.

---

## Relationships Summary

```
admin_user ──< deployment

vault ──< endpoint (vault_id override)
vault ──< global_settings (default_vault_id)

agent_registration_token ──< endpoint (1:1 in practice)

endpoint ──< gpu_resource
endpoint ──< model_artifact
endpoint ──< deployment

model ──< model_artifact
model ──< deployment

model_artifact ──< deployment

deployment ──< deployment_event
```

---

## Migrations

- **Tool:** Alembic, configured against the SQLAlchemy 2.x `MetaData` from the app.
- **Location:** `backend/migrations/versions/` in the repository.
- **Naming convention:** `NNNN_short_description.py` where `NNNN` is the autogenerated sequence (e.g., `0001_initial.py`, `0002_add_vault_pinning.py`).
- **Run on startup:** The control plane container entrypoint runs `alembic upgrade head` before starting `krelix-api` / `krelix-worker`.
- **Initial migration scope:** All entities above are part of `0001_initial.py`. Subsequent migrations are per-feature.
- **Generation discipline:** Use `alembic revision --autogenerate -m "..."` against the live ORM as the baseline, but **always hand-review the generated migration** — autogeneration is not perfect for JSONB indexes, check constraints with `CHECK IN (...)`, or partial unique indexes.

---

## Seed Data

A single Alembic data migration (e.g., `0002_seed_defaults.py`) seeds the following on a fresh install:

- `global_settings` row with id=1: `default_hot_tier_path='/var/lib/krelix/hot'`, `default_vault_id=NULL`, `eviction_policy_type='percent_free'`, `eviction_threshold=15.0`, `auto_iteration_retry_budget=5`.
- No `admin_user` seeded — first-time setup flow prompts the operator to create their admin account.
- No `huggingface_credential` seeded — operator enters via UI.
- No `vault` seeded — operator creates as needed.
- No `endpoint` seeded.

The first-run flow on the control plane: on visiting any UI route, if no `admin_user` exists, redirect to a one-time setup page that creates the first admin user, then the operator is logged in.
