# API Contracts — Krelix

Two distinct surfaces, separated by URL prefix:

- **`/api/v1/...`** — operator-facing API consumed by the Krelix Web UI (and any future external tool). Session-cookie authentication.
- **`/agent/v1/...`** — host-agent-facing protocol used only by registered host agents. Bearer-token authentication using the agent registration token.

FastAPI auto-generates an OpenAPI schema (served at `/openapi.json`) for the `/api/v1/...` surface. The `/agent/v1/...` surface is internal and may not be published in the OpenAPI doc, but is documented in this file.

---

## Conventions (apply to both surfaces)

- **Base paths:** `/api/v1` and `/agent/v1`.
- **Content type:** `application/json` for request and response bodies. Streaming endpoints use `text/event-stream` (SSE) or WebSocket protocol.
- **Authentication:**
  - **Operator surface:** HTTP-only cookie `krelix_session` set after login. CSRF token required for mutating verbs (POST/PUT/PATCH/DELETE) — sent as `X-CSRF-Token` header, paired with a non-HTTP-only cookie of the same name.
  - **Agent surface:** `Authorization: Bearer <agent-registration-token>` header on initial registration; after registration, the agent's persistent WebSocket connection is authenticated by the same token.
- **Error format** (uniform across both surfaces):

  ```json
  {
    "error": {
      "code": "string-error-code",
      "message": "Human-readable summary.",
      "details": { "...optional contextual fields..." }
    }
  }
  ```

  Error `code` values are stable strings (e.g., `endpoint_not_found`, `model_not_found_on_hf`, `agent_not_connected`, `hf_token_missing`, `validation_error`). The UI maps `code` to friendly messages; debug callers use `message` and `details`.

- **Status codes:**
  - `200 OK` — successful read or non-resource mutation.
  - `201 Created` — successful resource creation; `Location` header points to the new resource.
  - `202 Accepted` — long-running operation queued (e.g., starting a deployment).
  - `204 No Content` — successful mutation with no body (e.g., delete).
  - `400 Bad Request` — malformed JSON / missing required field.
  - `401 Unauthorized` — no/invalid session or token.
  - `403 Forbidden` — authenticated but not allowed (rare in single-operator v1; reserved).
  - `404 Not Found` — unknown resource.
  - `409 Conflict` — state conflict (e.g., trying to deploy when endpoint is offline, vault name collision).
  - `422 Unprocessable Entity` — validation error (Pydantic). `details` contains field-level error list.
  - `500 Internal Server Error` — unexpected.

- **Pagination** (list endpoints): query params `limit` (default 25, max 100) and `cursor` (opaque). Response includes `next_cursor` (nullable) and `total` when cheap to compute, omitted otherwise.

- **Timestamps:** ISO-8601 UTC strings (e.g., `"2026-05-19T14:00:00Z"`) in responses; same in requests.

- **UUIDs:** sent and received as strings (canonical hyphenated form).

---

## Operator-Facing Endpoints (`/api/v1`)

### Auth

#### `POST /api/v1/auth/setup` — first-time admin creation

Available only when zero `admin_user` rows exist. Creates the first admin and logs them in (sets session cookie).

**Request:**
```json
{ "username": "string", "password": "string" }
```

**Response (201):** `{ "id": "uuid", "username": "string" }`

**Errors:** `409 setup_already_complete` if an admin already exists.

**Maps to:** First-run experience prerequisite for all stories.

---

#### `POST /api/v1/auth/login`

**Request:** `{ "username": "string", "password": "string" }`

**Response (200):** `{ "id": "uuid", "username": "string" }` + session cookie set.

**Errors:** `401 invalid_credentials`.

---

#### `POST /api/v1/auth/logout`

**Response (204):** session cleared.

---

#### `GET /api/v1/auth/me`

**Response (200):** `{ "id": "uuid", "username": "string" }` or `401`.

---

### Global settings

#### `GET /api/v1/settings/global`

**Response (200):**
```json
{
  "default_hot_tier_path": "/var/lib/krelix/hot",
  "default_vault_id": "uuid-or-null",
  "eviction_policy_type": "percent_free",
  "eviction_threshold": 15.0,
  "auto_iteration_retry_budget": 5,
  "updated_at": "..."
}
```

#### `PATCH /api/v1/settings/global`

**Request:** any subset of the fields above.
**Response (200):** updated object.

**Maps to:** US-M-01 (resolved config powers endpoint deploys), US-M-05 (retry budget), US-M-09 (eviction policy).

---

### HuggingFace credential

#### `GET /api/v1/settings/huggingface`

**Response (200):** `{ "has_token": true, "label": "optional string", "updated_at": "..." }` — token value never returned.

#### `PUT /api/v1/settings/huggingface`

**Request:** `{ "token": "hf_...", "label": "optional string" }`

**Response (204):** stored encrypted.

#### `DELETE /api/v1/settings/huggingface`

**Response (204).**

**Maps to:** US-M-02.

---

### Vaults

#### `GET /api/v1/vaults` — list

**Response (200):** `{ "items": [Vault], "total": int }`

#### `POST /api/v1/vaults` — create

**Request:** `{ "name": "string", "description": "string?", "mount_path": "/mnt/krelix-vault" }`
**Response (201):** Vault.
**Errors:** `409 vault_name_taken`.

#### `GET /api/v1/vaults/{id}`
**Response (200):** Vault.

#### `PATCH /api/v1/vaults/{id}`
**Request:** partial Vault.
**Response (200):** Vault.

#### `DELETE /api/v1/vaults/{id}`
**Response (204):** soft delete. `409 vault_in_use` if any endpoint or global default still references it.

**Maps to:** US-M-01 (vault assignment is part of endpoint registration).

---

### Endpoints (GPU hosts)

#### `GET /api/v1/endpoints` — list

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "epyc-proxmox",
      "display_name": "Epyc Proxmox (GPU host)",
      "hostname": "epyc-proxmox.dropthe8.com",
      "agent_status": "online",
      "agent_version": "0.1.0",
      "last_heartbeat_at": "...",
      "resolved_config": {
        "hot_tier_path": "/var/lib/krelix/hot",
        "vault_id": "uuid",
        "vault_mount_path": "/mnt/krelix-vault",
        "eviction_policy_type": "percent_free",
        "eviction_threshold": 15.0,
        "auto_iteration_retry_budget": 5
      },
      "gpu_summary": { "total_gpus": 4, "total_vram_mb": 211968, "free_vram_mb": 188288 }
    }
  ],
  "total": 2
}
```

#### `POST /api/v1/endpoints` — start registration

**Request:**
```json
{
  "name": "epyc-proxmox",
  "display_name": "Epyc Proxmox (GPU host)",
  "hostname": "epyc-proxmox.dropthe8.com",
  "hot_tier_path": "/var/lib/krelix/hot",
  "vault_id": "uuid-or-null",
  "eviction_policy_type": "percent_free",
  "eviction_threshold": 15.0,
  "auto_iteration_retry_budget": 5
}
```
(All override fields are optional — omit to use global defaults.)

**Response (201):**
```json
{
  "endpoint": { "...as above..." },
  "registration_token": {
    "token": "krelix_agt_<long-bearer-string>",
    "label": "epyc-proxmox bootstrap"
  },
  "install_instructions": "Run on epyc-proxmox.dropthe8.com:\n\ndocker run -d ..."
}
```

The token plaintext is returned **exactly once** here and never again. Operator copies it into the host agent's config.

**Errors:** `409 endpoint_name_taken`, `409 hostname_in_use`, `422 invalid_vault`.

**Maps to:** US-M-01.

#### `GET /api/v1/endpoints/{id}`
**Response (200):** full endpoint detail, including all `gpu_resource` rows (with MIG state) and current resolved config.

#### `PATCH /api/v1/endpoints/{id}`
**Request:** partial endpoint (display_name, override fields). `name` and `hostname` are immutable after registration.
**Response (200):** endpoint.

#### `DELETE /api/v1/endpoints/{id}`
**Response (204):** soft delete. Triggers an outbound notification to the agent so it can shut down gracefully. `409 endpoint_has_active_deployments` if running deployments exist (operator must stop them first).

#### `POST /api/v1/endpoints/{id}/regenerate-token`
**Response (200):** new registration token (plaintext, once). Previous token is revoked.

#### `GET /api/v1/endpoints/{id}/gpus`
**Response (200):** list of `gpu_resource` rows including MIG state. Live VRAM usage may be included via short-cached values; for high-frequency use the WebSocket endpoint below.

#### `WS /api/v1/endpoints/{id}/gpus/live`
WebSocket. Pushes live GPU utilization and VRAM usage as the host agent reports them. Frame format (server → client):
```json
{
  "type": "gpu_state",
  "gpu_resource_id": "uuid",
  "vram_used_mb": 12345,
  "gpu_util_pct": 87,
  "temperature_c": 64,
  "power_w": 215,
  "reported_at": "..."
}
```

**Maps to:** US-M-04 (fit prediction needs current free VRAM); v2 monitoring (D phase).

---

### HuggingFace browsing

#### `GET /api/v1/hf/search`

**Query parameters:**
| Name | Type | Required | Notes |
|------|------|----------|-------|
| q | string | no | search term |
| task | string | no | e.g., `text-generation` |
| format | string | no | `safetensors` / `gguf` / `pt` |
| quantization | string | no | e.g., `awq`, `gptq`, `fp16` |
| limit | int | no | default 25, max 100 |
| cursor | string | no | opaque |

**Response (200):**
```json
{
  "items": [
    {
      "hf_model_ref": "Qwen/Qwen2.5-14B-Instruct-AWQ",
      "declared_license": "apache-2.0",
      "gated": false,
      "primary_format": "safetensors",
      "primary_quantization": "awq-4bit",
      "estimated_size_bytes": 9876543210,
      "downloads_last_month": 12345
    }
  ],
  "next_cursor": "...",
  "total": null
}
```

**Errors:** `502 hf_unreachable`, `429 hf_rate_limited`.

#### `GET /api/v1/hf/models/{owner}/{name}`

**Response (200):** full HF metadata snapshot (model card frontmatter, file manifest, gating status, resolved-revision-on-`main`).

#### `POST /api/v1/hf/models/{owner}/{name}/refresh`

Force re-fetch from HF and update the Krelix `model` cache. Returns the updated record.

**Maps to:** US-M-03.

---

### Models (Krelix's cache)

#### `GET /api/v1/models`
**Response (200):** list of `model` rows Krelix has seen.

#### `GET /api/v1/models/{id}`
**Response (200):** full `model` row including JSONB metadata, plus list of all `model_artifact` rows across endpoints.

**Maps to:** US-S-02 (license metadata at deployment time), US-S-03 (history).

---

### Model artifacts (per-endpoint inventory)

#### `GET /api/v1/endpoints/{endpoint_id}/artifacts`
**Response (200):** list of artifacts on this endpoint (model, revision, in_hot, in_vault, pinned, last_used_at, sizes).

#### `DELETE /api/v1/endpoints/{endpoint_id}/artifacts/{artifact_id}`
**Response (202):** queued; agent removes from both tiers. `409 artifact_in_use` if a running deployment is using it.

#### `POST /api/v1/endpoints/{endpoint_id}/artifacts/{artifact_id}/pin`
**Response (200):** `{ "pinned": true }`.

#### `DELETE /api/v1/endpoints/{endpoint_id}/artifacts/{artifact_id}/pin`
**Response (200):** `{ "pinned": false }`.

**Maps to:** pinning behavior in the eviction policy; supports US-S-03.

---

### Fit prediction

#### `GET /api/v1/fit-predictions`

**Query parameters:**
| Name | Type | Required | Notes |
|------|------|----------|-------|
| model_ref | string | yes | HF model reference; uses Krelix's cached metadata; refresh first if needed |
| endpoint_id | uuid | yes | |

**Response (200):**
```json
{
  "prediction": "fits_comfortably",
  "basis": {
    "model_estimated_size_mb": 9412,
    "endpoint_total_vram_mb": 211968,
    "endpoint_free_vram_mb": 188288,
    "largest_single_gpu_free_vram_mb": 96000,
    "considers_offload": false
  }
}
```

`prediction` is one of `fits_comfortably`, `needs_offload`, `wont_fit`.

**Errors:** `404 model_not_found_on_hf`, `404 endpoint_not_found`, `409 agent_not_connected` (live VRAM not available).

**Maps to:** US-M-04. Predictions made via this endpoint are not persisted; the prediction is re-recorded on the `deployment` row when a deploy is initiated, for accuracy measurement.

---

### Deployments

#### `GET /api/v1/deployments` — list with filters

**Query parameters:**
| Name | Type | Required | Notes |
|------|------|----------|-------|
| status | string[] | no | filter by one or more status values |
| endpoint_id | uuid | no | |
| model_id | uuid | no | |
| since | timestamp | no | initiated_at >= since |
| limit, cursor | | no | pagination |

**Response (200):** `{ "items": [Deployment], "next_cursor": "...", "total": int }`

#### `POST /api/v1/deployments` — initiate deployment

**Request:**
```json
{
  "endpoint_id": "uuid",
  "model_ref": "Qwen/Qwen2.5-14B-Instruct-AWQ",
  "model_revision": "optional-explicit-revision",
  "gpu_indices": [0],
  "initial_config_overrides": { "max_model_len": 4096 }
}
```

`model_revision` is optional — if omitted, Krelix resolves the current `main` and pins to that resolved commit.
`gpu_indices` is optional — if omitted, the agent picks the best fit per the fit-prediction basis.
`initial_config_overrides` is optional — operator-supplied vLLM args that seed the auto-iteration loop (US-C-02).

**Response (202):**
```json
{
  "id": "uuid",
  "status": "pending",
  "endpoint_id": "uuid",
  "model_id": "uuid",
  "resolved_revision": "abc123...",
  "fit_prediction_at_initiation": "fits_comfortably",
  "initiated_at": "..."
}
```

**Errors:** `404 model_not_found_on_hf`, `404 endpoint_not_found`, `409 agent_not_connected`, `409 endpoint_has_no_capacity`, `422 invalid_gpu_indices`.

**Maps to:** US-M-05.

#### `GET /api/v1/deployments/{id}`
**Response (200):** full deployment record, including `inference_url` when status is `running`.

**Maps to:** US-M-06, US-M-07, US-S-03.

#### `POST /api/v1/deployments/{id}/stop`
**Response (202):** queued. Eventual state: `stopped`.

**Errors:** `409 deployment_not_stoppable` (already terminal).

**Maps to:** US-M-09.

#### `GET /api/v1/deployments/{id}/events`
**Query parameters:** `since` (timestamp), `limit`.
**Response (200):** `{ "items": [DeploymentEvent], "next_cursor": "..." }`.

**Maps to:** US-M-07, US-S-03.

#### `WS /api/v1/deployments/{id}/status`

WebSocket. Live status transitions for this deployment. Server → client frames:
```json
{ "type": "status_changed", "from": "downloading", "to": "starting", "at": "..." }
{ "type": "iteration", "attempt": 2, "reason": "OOM at load", "adjusted_args": { "max_model_len": 4096 }, "at": "..." }
{ "type": "running", "inference_url": "http://...", "at": "..." }
```

**Maps to:** US-M-07.

#### `SSE /api/v1/deployments/{id}/logs`

Server-Sent Events. Live-tails the vLLM container's stdout/stderr as relayed from the host agent. Each event:
```
event: log
data: { "ts": "...", "stream": "stdout"|"stderr", "line": "..." }
```

Supports `?from=last-N-lines` (default 200) for an initial buffer flush, then live tail.

**Maps to:** US-M-08.

---

## Agent-Facing Endpoints (`/agent/v1`)

These are consumed only by registered Krelix host agents. **Bearer token auth using the agent's registration token.**

### `POST /agent/v1/register`

Called once by a freshly-installed host agent. The agent presents its registration token in `Authorization: Bearer ...` and identifies itself.

**Request:**
```json
{
  "agent_version": "0.1.0",
  "agent_runtime_mode": "docker",
  "host_info": { "hostname": "...", "os": "...", "kernel": "...", "docker_version": "...-or-null", "nvidia_driver": "..." },
  "engines_available": [
    { "name": "vllm", "version": "0.6.4", "launcher": "container:ghcr.io/.../vllm:0.6.4" }
  ],
  "gpus": [
    {
      "nvml_uuid": "GPU-...",
      "gpu_index": 0,
      "model_name": "NVIDIA RTX A4000",
      "vram_total_mb": 16384,
      "compute_capability": "8.6",
      "mig_capable": false,
      "mig_enabled_on_parent": false,
      "mig_profile": null,
      "parent_nvml_uuid": null
    }
  ]
}
```

`agent_runtime_mode` is one of `docker` or `systemd`. `engines_available[].launcher` describes how the engine is invoked: `container:<image-ref>` in Docker mode, `subprocess:<absolute-path-to-python> <module>` in systemd mode.

**Response (200):**
```json
{
  "endpoint_id": "uuid",
  "resolved_config": {
    "hot_tier_path": "/var/lib/krelix/hot",
    "vault_mount_path": "/mnt/krelix-vault",
    "eviction_policy_type": "percent_free",
    "eviction_threshold": 15.0,
    "auto_iteration_retry_budget": 5
  },
  "stream_url": "wss://krelix-control.dropthe8.com/agent/v1/stream"
}
```

After successful registration the agent's token is marked `consumed_at`. The agent then opens the WebSocket at `stream_url`.

**Errors:** `401 invalid_token`, `409 token_already_consumed`.

---

### `WS /agent/v1/stream` — persistent bidirectional channel

Authenticated by the same bearer token. The agent **initiates** the connection and keeps it open. Krelix sends commands; the agent sends events.

**Server → agent frame types** (commands):
```json
{ "type": "deploy", "id": "msg-uuid", "payload": {
    "deployment_id": "uuid",
    "model_ref": "...",
    "resolved_revision": "...",
    "gpu_indices": [0],
    "initial_config": { ... },
    "retry_budget": 5
}}

{ "type": "stop_deployment", "id": "...", "payload": { "deployment_id": "uuid" } }

{ "type": "remove_artifact", "id": "...", "payload": { "artifact_id": "uuid", "model_ref": "...", "resolved_revision": "..." } }

{ "type": "pin_artifact", "id": "...", "payload": { "artifact_id": "uuid", "pinned": true } }

{ "type": "refresh_config", "id": "...", "payload": { } }
```

**Agent → server frame types** (events, statuses, streams):
```json
{ "type": "ack", "id": "msg-uuid", "result": "accepted" | "rejected", "error": null }

{ "type": "heartbeat", "at": "...", "stats": { "hot_tier_free_mb": ..., "vault_free_mb": ... } }

{ "type": "gpu_state", "gpu_resource_id": "...", "vram_used_mb": ..., "gpu_util_pct": ..., "...": "..." }

{ "type": "artifact_state", "model_ref": "...", "resolved_revision": "...",
    "in_hot_tier": true, "in_vault_tier": false, "hot_tier_size_bytes": ..., "vault_tier_size_bytes": null }

{ "type": "deployment_status", "deployment_id": "uuid",
    "status": "downloading"|"copying"|"starting"|"running"|"failed",
    "engine_handle": "...", "engine_runtime_mode": "docker"|"systemd",
    "internal_port": 8001, "inference_url": "...", "final_config": { ... },
    "iteration": { "attempt": 2, "reason": "OOM at load", "adjusted_args": { ... } },
    "failure_reason": null }

{ "type": "deployment_log", "deployment_id": "uuid", "ts": "...", "stream": "stdout"|"stderr", "line": "..." }

{ "type": "eviction_event", "deployment_id_or_null": null, "artifact_id": "uuid",
    "reason": "lru_below_threshold", "freed_bytes": ... }
```

Framing is JSON-over-WebSocket with the envelope `{ type, id?, ... }`. Specific binary encoding (msgpack) is a deferred decision (see [`architecture.md`](architecture.md) "Decisions Deferred to Implementation").

**Maps to:** the underlying mechanism behind every operator-facing endpoint that touches a host (deploy, stop, fit prediction, log streaming, status updates, eviction events).

---

### `GET /agent/v1/config`

Polling endpoint. Most config updates are pushed via `refresh_config` on the stream, but the agent can also pull on reconnect or on demand.

**Response (200):** the `resolved_config` block from `/agent/v1/register`.

---

## User-Story → Endpoint Traceability

| Story | Endpoints |
|-------|-----------|
| US-M-01 (register endpoint) | `POST /api/v1/endpoints`, `GET /api/v1/endpoints/{id}`, `PATCH`, `DELETE`, `POST .../regenerate-token`, `POST /agent/v1/register` |
| US-M-02 (HF credentials) | `GET/PUT/DELETE /api/v1/settings/huggingface` |
| US-M-03 (browse HF) | `GET /api/v1/hf/search`, `GET /api/v1/hf/models/{owner}/{name}`, `POST .../refresh` |
| US-M-04 (fit prediction) | `GET /api/v1/fit-predictions`, `GET /api/v1/endpoints/{id}/gpus`, `WS .../gpus/live` |
| US-M-05 (deploy w/ auto-iteration) | `POST /api/v1/deployments`, plus `deploy` / `deployment_status` over `/agent/v1/stream` |
| US-M-06 (URL) | `GET /api/v1/deployments/{id}` (returns `inference_url`) |
| US-M-07 (status) | `GET /api/v1/deployments`, `GET /api/v1/deployments/{id}`, `WS .../status`, `GET .../events` |
| US-M-08 (logs in UI) | `SSE /api/v1/deployments/{id}/logs`, plus `deployment_log` over `/agent/v1/stream` |
| US-M-09 (eject) | `POST /api/v1/deployments/{id}/stop`, plus `stop_deployment` over `/agent/v1/stream` |
| US-S-01 (revision pinning) | `model_revision` field on `POST /api/v1/deployments`; surfaced in deployment + artifact responses |
| US-S-02 (license metadata) | License fields included in HF search results, model details, and deployment responses |
| US-S-03 (deployment history) | `GET /api/v1/deployments` with `since` filter; deployments are never deleted |
| US-C-01 (download progress) | Carried via `deployment_status` events on the stream (with byte counts) |
| US-C-02 (config override) | `initial_config_overrides` field on `POST /api/v1/deployments` |
