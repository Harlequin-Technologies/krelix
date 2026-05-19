# T034 — Frontend HF browser + fit prediction display

**Status:** Not started
**Phase:** 6 — HuggingFace browsing + fit prediction
**Estimated session length:** 3 hr
**Depends on:** T020, T031, T032, T033
**Blocks:** T040 (frontend deploy flow uses the model page as the deploy entry point)
**Maps to:** US-M-03 (browse HF), US-M-04 (fit prediction).

---

## Objective

Build the `/models` route: a search page for HuggingFace browsing with filters (task / format / quantization), a model detail page showing metadata + license + per-endpoint fit predictions. This is the operator's main "find a model" surface.

## Files to create

- `frontend/src/pages/ModelsPage.tsx` — search results + filters
- `frontend/src/pages/models/ModelDetailPage.tsx` — `/models/:owner/:name`
- `frontend/src/pages/models/FitPredictionGrid.tsx` — per-endpoint prediction display
- `frontend/src/hooks/useHfSearch.ts`, `useModelDetail.ts`, `useFitPrediction.ts`

## Files to modify

- `frontend/src/router.tsx` — add `/models` and `/models/:owner/:name`
- `frontend/src/layouts/AppLayout.tsx` — add "Models" to nav

## Steps

1. `ModelsPage.tsx`:
   - Search box (`q` query), filter pills (Task: Text Generation / Embeddings; Format: safetensors / GGUF; Quantization: AWQ / GPTQ / FP16 / etc.).
   - Results grid with card per model: name, license badge (color-coded — apache-2.0 / mit green, "other" or missing → yellow, gated → red lock icon), size, format, quantization, downloads/month.
   - Click → navigate to `/models/:owner/:name`.
   - "No HF token configured" empty state with a link to `/settings`.
2. `ModelDetailPage.tsx`:
   - Header: name, license, downloads, gated indicator.
   - Sections: README/model card summary (rendered with `react-markdown` + sanitizer plugin), file manifest table, per-endpoint `FitPredictionGrid`.
   - "Deploy" CTA — gated; in this ticket it's a placeholder button that opens a "coming in Phase 7" tooltip. The full deploy flow is T040.
3. `FitPredictionGrid.tsx`:
   - Fetches `useEndpointsList`, then for each online endpoint, fetches `useFitPrediction(model_ref, endpoint_id)`.
   - Renders a card per endpoint: endpoint name, traffic-light dot (green=fits, yellow=offload, red=won't fit), `basis` numbers (working set MB, free VRAM, etc.).
   - Offline endpoints show "agent offline — start the agent to see fit prediction."
4. Add `react-markdown` and `rehype-sanitize` to frontend deps (sanitize the HF model card content).

## Acceptance Criteria

- [ ] `/models` page renders search with filters; results populate via `/api/v1/hf/search`.
- [ ] Each result card shows the right metadata badges.
- [ ] No HF token → empty state directing to Settings.
- [ ] `/models/:owner/:name` detail page shows model card content (sanitized), file manifest, and a per-endpoint fit grid.
- [ ] Per-endpoint fit predictions render correctly for online endpoints; offline endpoints show the appropriate message.
- [ ] License badges are color-coded; gated models show a lock indicator.
- [ ] `react-markdown` HTML is sanitized via `rehype-sanitize` (no raw HTML injection).
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm test` exit 0.

## Out of Scope

- Deploy flow itself — T040.
- Saved searches / favorites — not in v1.
- Refresh-from-HF UI button — backend supports it but UI auto-refreshes via TanStack Query staleness (5 min for search, 10 min for model details).

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
