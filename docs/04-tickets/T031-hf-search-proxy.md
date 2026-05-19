# T031 — HuggingFace search + model metadata API (proxy through control plane)

**Status:** Not started
**Phase:** 6 — HuggingFace browsing + fit prediction
**Estimated session length:** 3 hr
**Depends on:** T018 (HF credential service)
**Blocks:** T032, T033, T034
**Maps to:** `api-contracts.md` HuggingFace browsing section; `architecture.md` "Control Plane … no direct HF I/O" — but for **search and metadata** this is metadata-only and read-only, no model files, so it's acceptable per the spec.

---

## Objective

Implement server-side HF search and metadata fetching. The control plane does HF metadata queries (text/JSON only, no model bytes — those happen on the agent side per architecture). Results are returned to the UI and also cached lightly in Redis with short TTL.

**Clarification:** The architecture rule is "control plane does no direct model-file I/O and no HuggingFace network I/O for artifacts." Metadata queries are explicitly allowed — they're tiny JSON requests needed to populate the operator's search results before any download is initiated.

## Files to create

- `backend/src/krelix/api/v1/hf.py` — search, model detail, refresh routes
- `backend/src/krelix/services/hf_search.py` — wraps `huggingface_hub.HfApi` with the operator's stored token
- `backend/src/krelix/api/v1/schemas/hf_search.py` — `HfSearchItem`, `HfSearchResponse`, `HfModelDetailResponse`
- `backend/tests/test_hf_search.py` — mocked HF API responses

## Steps

1. `services/hf_search.py`:
   - Constructor takes an `AsyncSession` for reading the HF token via `HfCredentialService.get_token_plaintext()`.
   - `search(query: str, filters: dict, limit: int, cursor: str | None)` → uses `HfApi.list_models` with `search`, `filter`, `limit`, `sort` params. Returns list of `HfSearchItem` shaped objects.
   - `get_model_details(hf_model_ref)` → uses `HfApi.model_info` to fetch file manifest + model card frontmatter + license + gating status.
2. `api/v1/hf.py`:
   - `GET /hf/search` — query params: `q`, `task`, `format`, `quantization`, `limit`, `cursor`. Calls `hf_search.search`. Returns `HfSearchResponse`.
   - `GET /hf/models/{owner}/{name}` — calls `hf_search.get_model_details`. Returns full JSON.
   - `POST /hf/models/{owner}/{name}/refresh` — force-refresh path; bypasses any Redis cache.
3. Redis caching: search results cached under `krelix:hf:search:<hash-of-params>` with 300s TTL. Model details cached under `krelix:hf:model:<ref>` with 600s TTL.
4. Token absent → 422 `hf_token_missing` ("Please add a HuggingFace token in Settings before browsing").
5. HF API errors (rate limit, 5xx, timeouts) → 502 `hf_unreachable` with structured details.

## Acceptance Criteria

- [ ] `GET /api/v1/hf/search` returns search results with metadata (license, format, quantization, size, downloads).
- [ ] `GET /api/v1/hf/models/{owner}/{name}` returns full model details (file manifest, model card summary, license, gating).
- [ ] Search results are cached in Redis for 300s; `refresh` forces re-fetch.
- [ ] Missing HF token → 422 with clear error.
- [ ] HF rate-limit (429) and 5xx propagate as 502 to the operator with structured `details`.
- [ ] All routes require operator auth.

## Out of Scope

- Persisting `model` rows in the DB — T032.
- Fit prediction — T033.
- Downloads (agent's job).

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
