# T010 — SQLAlchemy ORM models (all entities)

**Status:** Not started
**Phase:** 2 — Database foundation + auth
**Estimated session length:** 3-4 hr
**Depends on:** T009
**Blocks:** T011, T016
**Maps to:** `data-model.md` (all entities); `architecture.md` Component 3 (PostgreSQL).

---

## Objective

Define SQLAlchemy 2.x async declarative models for every entity in [`../03-technical/data-model.md`](../03-technical/data-model.md): `admin_user`, `agent_registration_token`, `vault`, `global_settings`, `endpoint`, `gpu_resource`, `huggingface_credential`, `model`, `model_artifact`, `deployment`, `deployment_event`. Type-safe via `Mapped[]` / `mapped_column`. Field names, types, constraints, indexes, and relationships must match the data-model spec exactly. No migration code yet — that's T011.

## Context

These models are the durable contract between the data model spec and the running code. Field-name drift is hostile to agents working downstream — every field in `data-model.md` must appear as a column with the same name, same type, and same constraints. JSONB columns must be typed as `dict[str, Any]` or a more specific Pydantic-validated shape where appropriate. Enums on `CHECK IN (...)` constraints should use SQLAlchemy `String` with a `CheckConstraint` rather than Postgres-native `ENUM` types — easier to migrate, easier to extend.

## Read for context

- [`../03-technical/data-model.md`](../03-technical/data-model.md) — **the spec**; every field must trace here
- [`../03-technical/architecture.md`](../03-technical/architecture.md) — for component context
- [`T009-settings-db-redis-connections.md`](T009-settings-db-redis-connections.md) — engine and base setup

## Files to create

- `backend/src/krelix/models/__init__.py` — re-exports all model classes and `Base`
- `backend/src/krelix/models/base.py` — `Base = declarative_base()` (SQLAlchemy 2 style: `class Base(DeclarativeBase): ...`); shared `id`, `created_at`, `updated_at` mixins; soft-delete mixin where applicable
- `backend/src/krelix/models/auth.py` — `AdminUser`, `AgentRegistrationToken`
- `backend/src/krelix/models/storage.py` — `Vault`, `GlobalSettings`, `HuggingFaceCredential`
- `backend/src/krelix/models/fleet.py` — `Endpoint`, `GpuResource`
- `backend/src/krelix/models/catalog.py` — `Model`, `ModelArtifact`
- `backend/src/krelix/models/deployments.py` — `Deployment`, `DeploymentEvent`
- `backend/tests/test_models.py` — instantiate each model with minimum required fields, assert no errors; validate enum constraint behaviors

## Files to modify

- None (T009 set up the engine; this ticket only adds model classes)

## Files to NOT touch

- `agent/`, `frontend/`
- Migrations (T011)
- Anything under `docs/`

## Steps

1. **Write `backend/src/krelix/models/base.py`** with SQLAlchemy 2 style:
   ```python
   import uuid
   from datetime import datetime
   from typing import Any
   from sqlalchemy import DateTime, MetaData, func
   from sqlalchemy.dialects.postgresql import JSONB, UUID
   from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

   metadata = MetaData(naming_convention={
       "ix": "ix_%(column_0_label)s",
       "uq": "uq_%(table_name)s_%(column_0_name)s",
       "ck": "ck_%(table_name)s_%(constraint_name)s",
       "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
       "pk": "pk_%(table_name)s",
   })

   class Base(DeclarativeBase):
       metadata = metadata
       type_annotation_map = {dict[str, Any]: JSONB}

   class UUIDPrimaryKeyMixin:
       id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

   class TimestampMixin:
       created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
       updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

   class SoftDeleteMixin:
       deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
   ```
   - The naming convention is critical — it gives every constraint a predictable name for Alembic.

2. **Write `models/auth.py`** with:
   - `AdminUser(Base, UUIDPrimaryKeyMixin, TimestampMixin)` with `username` (unique), `password_hash`, `last_login_at`.
   - `AgentRegistrationToken(Base, UUIDPrimaryKeyMixin, TimestampMixin)` with `token_hash` (unique), `label`, `consumed_at`, `revoked_at`.

3. **Write `models/storage.py`:**
   - `Vault(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin)` with `name` (unique), `description` (nullable), `mount_path`.
   - `GlobalSettings(Base)` — **non-mixin** because of the singleton constraint. `id` is `INTEGER PRIMARY KEY CHECK (id = 1)` (use `mapped_column(Integer, primary_key=True)` + `CheckConstraint("id = 1", name="single_row")`). Fields: `default_hot_tier_path`, `default_vault_id` (FK nullable to vault.id), `eviction_policy_type` (String + CheckConstraint IN), `eviction_threshold` (Float), `auto_iteration_retry_budget` (Integer, default 5), `updated_at`.
   - `HuggingFaceCredential(Base)` — same singleton pattern (`id = 1`). Fields: `token_encrypted` (LargeBinary), `label` (nullable), `updated_at`.

4. **Write `models/fleet.py`:**
   - `Endpoint(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin)`:
     - Identity: `name` (unique active), `display_name`, `hostname`, `registration_token_id` (FK to `agent_registration_token.id`).
     - Agent state: `agent_status` (String + CheckConstraint IN `('never_connected','online','offline')`), `agent_version` (nullable), `agent_runtime_mode` (nullable, String + CheckConstraint IN `(NULL,'docker','systemd')`), `last_heartbeat_at`.
     - Override fields (all nullable): `hot_tier_path`, `vault_id` (FK), `eviction_policy_type` (String + CheckConstraint), `eviction_threshold` (Float), `auto_iteration_retry_budget` (Integer).
     - Relationships: `gpus = relationship("GpuResource", back_populates="endpoint", cascade="all, delete-orphan")`, `vault = relationship("Vault")`.
     - Unique constraint on `hostname` where `deleted_at IS NULL` — implement as a partial unique index in T011 migration (note in completion summary).
   - `GpuResource(Base, UUIDPrimaryKeyMixin, TimestampMixin)`:
     - `endpoint_id` (FK with ON DELETE CASCADE), `gpu_index`, `nvml_uuid`, `model_name`, `vram_total_mb`, `compute_capability` (nullable).
     - MIG fields: `mig_capable` (Boolean, default False), `mig_enabled_on_parent` (Boolean, default False), `mig_profile` (nullable), `parent_nvml_uuid` (nullable).
     - `last_reported_at` (timestamptz, nullable until first report).
     - Unique on `(endpoint_id, nvml_uuid)`. Index on `endpoint_id`. Index on `parent_nvml_uuid`.

5. **Write `models/catalog.py`:**
   - `Model(Base, UUIDPrimaryKeyMixin, TimestampMixin)`:
     - `hf_model_ref` (unique), `declared_license` (nullable), `declared_license_url` (nullable), `gated` (Boolean, default False), `primary_format` (nullable, CheckConstraint IN `(NULL,'safetensors','gguf','pt')`), `primary_quantization` (nullable), `estimated_size_bytes` (BigInteger, nullable), `hf_metadata` (JSONB, default `{}`), `last_metadata_fetched_at` (nullable).
   - `ModelArtifact(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin)`:
     - `model_id` (FK), `endpoint_id` (FK, ON DELETE CASCADE), `resolved_revision`, `in_hot_tier` (Boolean, default False), `in_vault_tier` (Boolean, default False), `hot_tier_size_bytes` (BigInteger, nullable), `vault_tier_size_bytes` (BigInteger, nullable), `pinned` (Boolean, default False), `last_used_at` (nullable), `download_completed_at` (nullable).
     - Unique on `(endpoint_id, model_id, resolved_revision)`.
     - Indexes: `(endpoint_id, last_used_at)`, `(endpoint_id, in_hot_tier)`.

6. **Write `models/deployments.py`:**
   - `Deployment(Base, UUIDPrimaryKeyMixin, TimestampMixin)` — **no soft-delete; deployments are durable history**:
     - `endpoint_id` (FK), `model_id` (FK), `model_artifact_id` (FK, nullable), `resolved_revision`, `status` (String + CheckConstraint IN `('pending','provisioning','downloading','copying','starting','running','stopped','failed')`).
     - Engine info: `engine` (default `'vllm'`), `engine_version` (nullable), `gpu_indices` (ARRAY(Integer), default `[]`), `initial_config` (JSONB), `final_config` (JSONB, nullable), `iteration_count` (Integer, default 0).
     - Runtime info: `inference_url` (nullable), `internal_port` (Integer, nullable), `engine_handle` (nullable), `engine_runtime_mode` (nullable, CheckConstraint IN `(NULL,'docker','systemd')`).
     - Prediction: `fit_prediction_at_initiation` (String + CheckConstraint IN), `fit_prediction_basis` (JSONB, default `{}`), `observed_outcome` (nullable, CheckConstraint IN `(NULL,'fit','needed_offload','wont_fit')`).
     - Lifecycle: `failure_reason` (nullable), `initiated_at` (default now()), `started_at` (nullable), `stopped_at` (nullable), `failed_at` (nullable).
     - `created_by_user_id` (FK to `admin_user.id`).
     - Indexes: `endpoint_id`, `(endpoint_id, status)`, `model_id`, `initiated_at DESC`.
   - `DeploymentEvent(Base, UUIDPrimaryKeyMixin)`:
     - `deployment_id` (FK, ON DELETE CASCADE), `event_at` (default now()), `event_type`, `from_status` (nullable), `to_status` (nullable), `message` (nullable), `payload` (JSONB, default `{}`).
     - Index on `(deployment_id, event_at DESC)`.

7. **Write `models/__init__.py`** that re-exports `Base` and every model class.

8. **Write `backend/tests/test_models.py`** — instantiate each model with required-only fields, assert it can be added to a session without error. Don't commit (just `session.add(...)` and `session.flush()` in a rolled-back transaction). Verify enum CheckConstraints raise on invalid values when flushed.

9. **Run `mypy` on `models/`** to make sure SQLAlchemy 2's `Mapped[]` typing is happy. Pydantic mypy plugin and SQLAlchemy's mypy plugin should both be active per T002's `pyproject.toml`.

10. **Verify:**
    - `cd backend && uv run mypy src` clean
    - `cd backend && uv run pytest tests/test_models.py` green (each model instantiates cleanly; CheckConstraint violations raise)

## Acceptance Criteria

- [ ] All 11 entities from `data-model.md` exist as SQLAlchemy declarative classes with column names exactly matching the spec.
- [ ] Every CheckConstraint and uniqueness constraint from `data-model.md` is present (some unique-on-active-rows constraints are deferred to T011's partial-index migration — call those out in completion summary).
- [ ] Foreign keys are configured with correct `ON DELETE` behavior matching the spec (CASCADE where specified, default RESTRICT otherwise).
- [ ] JSONB columns are typed `dict[str, Any]` and serialize/deserialize correctly.
- [ ] `GpuResource` has the four new MIG columns (`mig_capable`, `mig_enabled_on_parent`, `mig_profile`, `parent_nvml_uuid`).
- [ ] `Endpoint` has the `agent_runtime_mode` column.
- [ ] `Deployment` has `engine_handle` and `engine_runtime_mode` (renamed from the older `container_id` per the dual-mode update).
- [ ] `Endpoint` and `Vault` are soft-deletable (`deleted_at` on the model and excluded from default queries — implement a `not_deleted()` helper in `base.py` or a query option in T011).
- [ ] `GlobalSettings` and `HuggingFaceCredential` enforce single-row constraints (`CHECK (id = 1)`).
- [ ] `uv run mypy src/krelix/models` is clean.
- [ ] `uv run pytest tests/test_models.py` is green.
- [ ] The model module files compile and import cleanly: `python -c "from krelix.models import Base, AdminUser, Vault, GlobalSettings, Endpoint, GpuResource, Model, ModelArtifact, Deployment, DeploymentEvent, AgentRegistrationToken, HuggingFaceCredential"` succeeds.

## Out of Scope (for this ticket)

- Migrations — T011
- Any data access / repository layer — comes alongside the API tickets that need it
- Seed data — T011
- Pydantic schemas for API serialization — those land alongside the API tickets that need them
- Query helpers (e.g., a `Repository` class) — not needed for v1; raw `session.execute(select(...))` is fine

## Notes

- SQLAlchemy 2's `Mapped[]` typing requires `from __future__ import annotations` or quoted strings in some Python+SQLAlchemy combinations. Test that mypy is happy.
- The "unique on `hostname` where `deleted_at IS NULL`" partial index is **not** representable in pure SQLAlchemy ORM-level constraints — it requires raw `Index(..., postgresql_where=...)`. Use that, or punt it to T011 as a migration-level partial unique index. Either is fine; document the choice in completion summary.
- Resist the urge to add convenience methods (`@property` calculations, `__repr__` beyond debug-friendly basics, etc.). Models should be data containers; logic lives elsewhere.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
