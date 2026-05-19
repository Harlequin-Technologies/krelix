# T032 — Model entity persistence + revision resolution + license capture

**Status:** Not started
**Phase:** 6 — HuggingFace browsing + fit prediction
**Estimated session length:** 2 hr
**Depends on:** T031
**Blocks:** T033, T035, T037
**Maps to:** `data-model.md` `model` entity; US-S-01 (immutable revision pinning); US-S-02 (license metadata).

---

## Objective

When the operator interacts with a HF model (viewing details, starting a deploy), persist a `model` row in the Krelix database with declared license, format/quantization, estimated size, and full HF metadata snapshot. Provide a service to **resolve** `main` (or any branch ref) to an immutable commit hash for revision pinning per US-S-01.

## Files to create

- `backend/src/krelix/services/model_cache.py` — `upsert_model_from_hf(hf_model_ref)` + `resolve_revision(hf_model_ref, ref="main")`
- `backend/tests/test_model_cache.py`

## Files to modify

- `backend/src/krelix/api/v1/hf.py` — `GET /hf/models/{owner}/{name}` now also upserts the `model` row as a side effect (always returns cached HF JSON; persisting is best-effort, doesn't block the response on transient DB errors)

## Steps

1. `model_cache.py`:
   - `upsert_model_from_hf(db, hf_search_service, hf_model_ref)`:
     - Call `hf_search_service.get_model_details(hf_model_ref)`.
     - From the response, extract: declared_license, declared_license_url, gated flag, primary_format (inspect file extensions in the manifest; `.safetensors` → safetensors, `.gguf` → gguf, `.bin/.pt` → pt; tiebreaker: most common), primary_quantization (from model card frontmatter `quantization_method` or pattern-match in the name: AWQ/GPTQ/FP8/etc.), estimated_size_bytes (sum of weights file sizes), raw `hf_metadata`.
     - Upsert into `model` table (use `ON CONFLICT (hf_model_ref) DO UPDATE`).
     - Return the upserted row.
   - `resolve_revision(db, hf_search_service, hf_model_ref, ref="main")`:
     - Calls `HfApi.model_info(hf_model_ref, revision=ref)` and reads `sha` from the response.
     - Returns the commit hash. Used by deploy flow (T035) to pin the deployment to an immutable revision.

## Acceptance Criteria

- [ ] Viewing a model in the HF browser persists a `model` row with license + format + quantization + size + raw metadata.
- [ ] `resolve_revision("Qwen/Qwen2.5-14B-Instruct-AWQ", "main")` returns a commit SHA.
- [ ] Re-fetching the same model updates the existing row (no duplicates).
- [ ] License extraction handles missing license metadata gracefully (NULL in DB; gated flag still captured if applicable).
- [ ] Primary-format/quantization detection handles common cases (safetensors+AWQ, GGUF, FP16, etc.); ambiguous cases default to NULL.

## Out of Scope

- Fit prediction — T033.
- Refreshing all stored models on a schedule — operator can `POST /hf/models/{owner}/{name}/refresh` per model.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
