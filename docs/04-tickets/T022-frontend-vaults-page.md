# T022 — Frontend vaults page (CRUD)

**Status:** Not started
**Phase:** 3 — Vault, settings, HF credential management
**Estimated session length:** 2.5 hr
**Depends on:** T019, T020
**Blocks:** None in Phase 3
**Maps to:** `api-contracts.md` Vaults section.

---

## Objective

Build the `/vaults` page with a list view, an inline create form, an edit modal/drawer, and a delete confirm with clear error display when the vault is in use.

## Context

A small CRUD UI. Operators typically have 1–3 vaults. The page is reachable from the top-nav "Vaults" link.

## Read for context

- [`../03-technical/api-contracts.md`](../03-technical/api-contracts.md) — Vaults section
- [`T019-vault-crud-api.md`](T019-vault-crud-api.md) — backend endpoints + error codes
- [`T020-frontend-auth-shell-api-client.md`](T020-frontend-auth-shell-api-client.md) — established frontend patterns
- [`T021-frontend-settings-page.md`](T021-frontend-settings-page.md) — `useVaultsList` was introduced there; reuse it

## Files to create

- `frontend/src/pages/VaultsPage.tsx`
- `frontend/src/pages/vaults/VaultListView.tsx`
- `frontend/src/pages/vaults/VaultFormDrawer.tsx` — create + edit form, rendered in a side drawer or modal
- `frontend/src/pages/vaults/DeleteVaultDialog.tsx`
- `frontend/src/hooks/useVaultMutations.ts` — create/patch/delete hooks

## Files to modify

- `frontend/src/router.tsx` — add `/vaults` route inside `AppLayout`
- `frontend/src/layouts/AppLayout.tsx` — make the "Vaults" nav link real

## Files to NOT touch

- Backend
- Other frontend pages (T020, T021)

## Steps

1. **Write `useVaultMutations.ts`** with three mutations: create, patch (takes id + body), delete (takes id). Each invalidates `['vaults', 'list']` on success.

2. **Write `VaultListView.tsx`** — a simple table:
   - Columns: Name, Mount Path, Description (truncated), Updated, Actions (Edit, Delete buttons)
   - Empty state: "No vaults yet. Create one to assign it to GPU endpoints."
   - Below the table: a "Create vault" button that opens the form drawer.

3. **Write `VaultFormDrawer.tsx`** — a side-drawer (or modal — pick the simpler option for v1; Tailwind makes a slide-over straightforward) with three fields: name, mount path, description. Submit button label is "Create" or "Save" depending on whether it's editing or creating. Validation errors from the backend (e.g., 409 `vault_name_taken`, 422 invalid path) surface inline next to the relevant field.

4. **Write `DeleteVaultDialog.tsx`** — confirm dialog. On confirm, call the delete mutation. If the backend returns 409 `vault_in_use_by_endpoint` or `vault_in_use_by_globals`, show a clear error: "This vault is in use by [N] endpoint(s) and the global default. Reassign them first, then try again." The error `details` payload from the API includes which endpoints — surface them.

5. **Write `VaultsPage.tsx`** — composes list view + drawer + dialog. State for "form open" and "deleting which" lives in the page component (or a tiny custom hook).

6. **Wire the route in `router.tsx`** and update the AppLayout nav.

7. **Manual smoke test:**
   - Create a vault named "primary" with mount path `/mnt/krelix-vault` → appears in list.
   - Edit it, change description → save → list shows update.
   - Set this vault as `default_vault_id` via the Settings page.
   - Try to delete it → 409, error message names "global default."
   - Clear the default in Settings, try delete again → success.
   - Try to create another vault with name "primary" (the now-deleted one) → succeeds (uniqueness only checks active rows).
   - Try `/vaults` while logged out → redirected to `/login`.

## Acceptance Criteria

- [ ] `/vaults` route renders inside the logged-in `AppLayout`.
- [ ] List view fetches from `/api/v1/vaults` and displays Name, Mount Path, Description, Updated, Actions.
- [ ] Empty state is friendly and informative.
- [ ] Create form validates required fields client-side and surfaces backend errors inline.
- [ ] Edit form pre-populates with the current row's values.
- [ ] Delete dialog confirms before calling DELETE; on 409, shows the specific reason and (when available) the list of blocking entities.
- [ ] After every successful mutation, the list refreshes (TanStack Query invalidation).
- [ ] All API calls flow through `fetchApi`.
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test` exit 0.

## Out of Scope (for this ticket)

- Drag-to-reorder or filtering / sorting — operator has few vaults; no need.
- Vault-to-endpoint reassignment UI inside this page — operator does that from the Endpoint settings (later phase).
- Vault filesystem connectivity test (does the path actually mount on hosts?) — that's the host agent's concern at deploy time.

## Notes

- Keep the form drawer simple — no fancy multi-step wizards. Three fields and a save button.
- The "form drawer" implementation can be a controlled component using Tailwind's transitions, or you can pull in `radix-ui/react-dialog` for accessibility. Either is fine; if you pull in Radix, surface it as a new dep.
- Resist building a "vault details" page with a separate route. The drawer is enough for v1's small vault counts.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
