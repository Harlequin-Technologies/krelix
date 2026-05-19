# T049 — Pin/unpin API + frontend artifact list per endpoint

**Status:** Not started
**Phase:** 10 — Two-tier storage + eviction
**Estimated session length:** 2 hr
**Depends on:** T026, T047
**Blocks:** None
**Maps to:** `api-contracts.md` `POST /api/v1/endpoints/{id}/artifacts/{artifact_id}/pin` + DELETE; pin functionality from T048.

---

## Objective

Implement the artifact-list / pin / unpin / remove endpoints and a small UI inside the endpoint detail page that lists current artifacts (in hot, vault, or both) and lets the operator pin/unpin/remove.

## Files to create

- `backend/src/krelix/api/v1/artifacts.py` — list / pin / unpin / remove
- `backend/src/krelix/api/v1/schemas/artifact.py`
- `frontend/src/pages/endpoints/EndpointArtifactsPanel.tsx`
- `frontend/src/hooks/useEndpointArtifacts.ts`
- `backend/tests/test_artifacts_api.py`

## Files to modify

- `backend/src/krelix/api/v1/router.py` — include artifacts router
- `frontend/src/pages/endpoints/EndpointListView.tsx` — expandable section: artifacts panel

## Steps

1. Backend:
   - `GET /api/v1/endpoints/{endpoint_id}/artifacts` — list `model_artifact` rows with model info joined.
   - `POST /api/v1/endpoints/{endpoint_id}/artifacts/{artifact_id}/pin` — set `pinned=True`; also send a `pin_artifact` command to the agent (so it updates its in-memory pin set immediately).
   - `DELETE /api/v1/endpoints/{endpoint_id}/artifacts/{artifact_id}/pin` — set `pinned=False`; send `unpin_artifact` command.
   - `DELETE /api/v1/endpoints/{endpoint_id}/artifacts/{artifact_id}` — send `remove_artifact` command to the agent (agent deletes both tiers); 409 `artifact_in_use` if a running deployment uses it.
2. Agent side: extend `_recv_loop` to handle `pin_artifact`, `unpin_artifact`, `remove_artifact` frames.
3. Frontend `EndpointArtifactsPanel`:
   - Table: Model + revision, Hot tier (size), Vault tier (size), Pinned (toggle), Last used, Remove button.
   - Pin/unpin toggles call the appropriate endpoint.
   - Remove confirms first; surfaces `artifact_in_use` errors clearly.

## Acceptance Criteria

- [ ] All four endpoints work per `api-contracts.md`.
- [ ] Pinning persists in DB and is honored by the next agent eviction sweep.
- [ ] Agent receives pin/unpin/remove commands and acts on them.
- [ ] Frontend panel renders artifacts with hot/vault sizes and pin state.
- [ ] Remove confirms; blocks if artifact is in use.
- [ ] Auth + CSRF enforced on mutating routes.

## Out of Scope

- Bulk pin/unpin — not v1.
- Predicted-soon-evicted indicator — not v1.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
