# T026 — Frontend endpoint pages (list + create + edit + install instructions)

**Status:** Not started
**Phase:** 4 — Endpoint registration + agent bootstrap protocol
**Estimated session length:** 4 hr
**Depends on:** T020, T023
**Blocks:** Phase 11 frontend polish (later we add GPU detail views, online/offline indicators backed by live WS state)
**Maps to:** `api-contracts.md` Endpoints section (operator-side); UI consumption of `EndpointCreatedResponse` (token + install instructions).

---

## Objective

Build the `/endpoints` page in the logged-in shell: a list view of registered endpoints (with online/offline status, GPU summary, and resolved config), a create flow that returns a one-time bootstrap token + install instructions, an edit drawer for the per-endpoint override fields, and a delete confirm with active-deployment guard messaging.

## Context

The single most operator-facing UX in Phase 4. The create flow's one-time token reveal is **critical** — operator must copy it now, never again. The install instructions need to be presentable as copy-paste blocks for both container mode and bare-metal mode.

## Read for context

- [`../03-technical/api-contracts.md`](../03-technical/api-contracts.md) — Endpoints section in full
- [`T023-endpoint-crud-api.md`](T023-endpoint-crud-api.md) — backend response shapes
- [`T020-frontend-auth-shell-api-client.md`](T020-frontend-auth-shell-api-client.md), [`T022-frontend-vaults-page.md`](T022-frontend-vaults-page.md) — established frontend patterns (drawer/dialog/list)

## Files to create

- `frontend/src/pages/EndpointsPage.tsx`
- `frontend/src/pages/endpoints/EndpointListView.tsx`
- `frontend/src/pages/endpoints/EndpointCreateFlow.tsx` — multi-step: form → token-reveal screen
- `frontend/src/pages/endpoints/EndpointEditDrawer.tsx`
- `frontend/src/pages/endpoints/DeleteEndpointDialog.tsx`
- `frontend/src/pages/endpoints/InstallInstructionsBlock.tsx` — copy-paste-friendly code block component
- `frontend/src/hooks/useEndpoints.ts` — list, get, create, patch, delete, regenerate-token mutations

## Files to modify

- `frontend/src/router.tsx` — add `/endpoints` route
- `frontend/src/layouts/AppLayout.tsx` — wire the "Endpoints" nav link

## Files to NOT touch

- Backend
- Auth shell (T020), Settings/Vaults pages (T021, T022)

## Steps

1. **Write `useEndpoints.ts`** with hooks: `useEndpointsList`, `useEndpoint(id)`, `useCreateEndpoint`, `usePatchEndpoint`, `useDeleteEndpoint`, `useRegenerateToken`. Each mutation invalidates `['endpoints', 'list']` and `['endpoints', id]` on success.

2. **Write `EndpointListView.tsx`** — a table:
   - Columns: Display Name, Hostname, Status (online/offline/never_connected with a colored dot), Agent runtime mode (docker/systemd/—), GPUs (count + total VRAM summary), Last heartbeat (relative time), Resolved vault (name or "—"), Actions (Edit / Delete / Regenerate token).
   - Empty state: "No endpoints registered yet. Add one to register a GPU host."
   - "Add endpoint" button → opens `EndpointCreateFlow`.

3. **Write `EndpointCreateFlow.tsx`** as a two-step UX in a drawer:
   - **Step 1 — Form:**
     - Required: `name` (auto-suggest from hostname, e.g., `epyc-proxmox` from `epyc-proxmox.dropthe8.com`; user-editable), `display_name`, `hostname` (FQDN).
     - Optional override fields (collapsed accordion, "Use global defaults" toggle if absent): hot tier path, vault selector (populated from `useVaultsList`), eviction policy type, eviction threshold, retry budget.
     - Submit calls `useCreateEndpoint`. On 409 → inline error on the relevant field.
   - **Step 2 — Token reveal:**
     - Big warning banner: "This token is shown **only once**. Copy it now."
     - The token in a monospace block with a "Copy" button (uses `navigator.clipboard.writeText`).
     - Below: a tabbed `InstallInstructionsBlock` (Container / Bare-metal tabs); each tab shows the relevant instructions string with the token placeholder already substituted, with a "Copy entire snippet" button.
     - "Done" button closes the drawer and refreshes the list.
   - If the operator closes the drawer at step 2 without copying, show a confirmation: "If you close now, you'll need to regenerate the token to get a new one." Allow them to confirm or cancel.

4. **Write `EndpointEditDrawer.tsx`** — form for the override fields only (name + hostname are immutable). Pre-populates with current values; setting a field to "Use global default" clears the override (i.e., sends `null` explicitly in the PATCH body using a sentinel `model_dump` approach).

5. **Write `DeleteEndpointDialog.tsx`** — confirm + delete; on 409 `endpoint_has_active_deployments`, show: "This endpoint has [N] active deployment(s). Stop them first, then try again." Provide a link to a (future) deployments page filtered by this endpoint (or just plain text for now).

6. **Write `InstallInstructionsBlock.tsx`** — a reusable component:
   - Props: `containerSnippet: string`, `bareMetalSnippet: string`, `token: string` (substituted into the placeholders).
   - Two tabs (`<button>` toggles, plain Tailwind, no external library needed).
   - Each tab shows a `<pre>` block with the snippet; a "Copy" button copies the whole snippet (with the token substituted) to the clipboard.
   - Visually distinguishable: monospaced font, dark-mode-friendly code styling.

7. **Add a small "Regenerate token" action** in the list view's action menu: opens a confirm dialog ("This invalidates the current agent's connection — it will reconnect after you paste the new token. Continue?"). On confirm, call `useRegenerateToken(id)`, then show the new token + install instructions in the same drawer UI used by `EndpointCreateFlow` step 2.

8. **Wire the route** in `router.tsx`; activate the nav link.

9. **Manual smoke test:**
   - Create endpoint `epyc-A4000` with hostname `epyc-proxmox.dropthe8.com`. Receive token. Copy. Close.
   - List shows the endpoint with status `never_connected`, no GPUs yet.
   - Edit → set hot_tier_path override → save → list reflects the change (resolved_config differs from defaults).
   - Edit → set hot_tier_path back to "Use global default" → resolved_config reverts.
   - Try Delete → succeeds (no deployments) → endpoint disappears from list.
   - Regenerate token on a different endpoint → new plaintext shown; previous one no longer authenticates (verify via curl from the test).
   - `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test` all exit 0.

## Acceptance Criteria

- [ ] `/endpoints` route renders inside the logged-in `AppLayout`.
- [ ] List view shows all registered endpoints with status, GPU summary, runtime mode, last heartbeat, resolved vault, and action buttons.
- [ ] Create flow has two steps: form, then token-reveal with install instructions.
- [ ] Token is displayed in a copy-friendly monospace block; "Copy" button works.
- [ ] Install instructions tabs (Container / Bare-metal) display the snippets returned by the backend with the token substituted.
- [ ] Closing the create drawer at step 2 prompts a "you'll need to regenerate" confirmation.
- [ ] Edit drawer allows clearing an override (sending `null` to clear back to global default).
- [ ] Edit drawer cannot change `name` or `hostname` (UI doesn't show them as editable).
- [ ] Delete dialog blocks on 409 with a clear active-deployments message.
- [ ] Regenerate-token reveals the new token in the same UI as initial creation.
- [ ] All API calls flow through `fetchApi` (CSRF handled automatically).
- [ ] Online/offline status indicator is visible but data comes from `agent_status` polled via the list query (15s stale time is fine for v1; real-time push lands in Phase 11).
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm test` exit 0.

## Out of Scope (for this ticket)

- Real-time online/offline status push (WebSocket from frontend) — Phase 11 (D-phase preparation).
- GPU detail panel inside the endpoint detail view — Phase 11; for v1, the list view shows count + total VRAM, that's it.
- MIG configuration UI (operator runs `nvidia-smi mig` externally per scope) — long-term parking lot.
- Endpoint detail page on its own route — list + drawer is enough for v1.

## Notes

- The "two-step create" UX matters a lot. Resist collapsing it to a single form — the token reveal needs prominence and the warning that it's only shown once needs space.
- The install instructions tabs use plain Tailwind + state; no Radix or Headless UI needed. Keep deps minimal.
- The "Copy to clipboard" pattern: `navigator.clipboard.writeText(text)` works in modern browsers on HTTPS or `localhost`. Document this for the operator if they hit issues on HTTP-only LAN deployments (suggest a "select all" fallback that selects the text inside the `<pre>`).

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
