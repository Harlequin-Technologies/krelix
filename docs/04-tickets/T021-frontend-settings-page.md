# T021 — Frontend settings page (global + HF token)

**Status:** Not started
**Phase:** 3 — Vault, settings, HF credential management
**Estimated session length:** 2.5 hr
**Depends on:** T017, T018, T020
**Blocks:** None in Phase 3 (T022 is independent)
**Maps to:** `api-contracts.md` Global settings + HuggingFace credential sections.

---

## Objective

Build the `/settings` page in the logged-in shell, with two sections: **Global Settings** (the singleton row's editable fields) and **HuggingFace Credential** (set/clear, never display).

## Context

Operator-facing page. Form-driven, no surprises. Both sections show "saved at" timestamps. Form submits go through `fetchApi` (which handles CSRF). The page is reachable from the top-nav "Settings" link added in T020.

## Read for context

- [`../03-technical/api-contracts.md`](../03-technical/api-contracts.md) — Global settings + HF credential sections
- [`T020-frontend-auth-shell-api-client.md`](T020-frontend-auth-shell-api-client.md) — established frontend patterns

## Files to create

- `frontend/src/pages/SettingsPage.tsx`
- `frontend/src/pages/settings/GlobalSettingsSection.tsx`
- `frontend/src/pages/settings/HfCredentialSection.tsx`
- `frontend/src/hooks/useGlobalSettings.ts` — TanStack Query hook (read + mutate)
- `frontend/src/hooks/useHfCredential.ts` — TanStack Query hook (status + put + delete)

## Files to modify

- `frontend/src/router.tsx` — add route `/settings` → `SettingsPage` inside the `AppLayout` tree
- `frontend/src/layouts/AppLayout.tsx` — make the "Settings" nav link work (it was a placeholder in T020)

## Files to NOT touch

- Backend
- Auth shell (T020) — finalized

## Steps

1. **Write `useGlobalSettings.ts`:**
   ```ts
   import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
   import { fetchApi } from '../api/client'
   import type { components } from '../api/gen/openapi'

   type GlobalSettings = components['schemas']['GlobalSettingsResponse']
   type Patch = components['schemas']['GlobalSettingsPatchRequest']

   const key = ['settings', 'global']

   export function useGlobalSettings() {
     return useQuery<GlobalSettings>({
       queryKey: key,
       queryFn: () => fetchApi('/api/v1/settings/global'),
     })
   }

   export function usePatchGlobalSettings() {
     const qc = useQueryClient()
     return useMutation<GlobalSettings, Error, Patch>({
       mutationFn: (body) => fetchApi('/api/v1/settings/global', { method: 'PATCH', body }),
       onSuccess: (data) => qc.setQueryData(key, data),
     })
   }
   ```

2. **Write `useHfCredential.ts`:**
   ```ts
   // Same pattern; queries /settings/huggingface (status) and exposes put + delete mutations.
   // On any mutation success, invalidate the status query.
   ```

3. **Write `GlobalSettingsSection.tsx`:**
   - Read current settings via `useGlobalSettings`.
   - Editable fields: hot tier path (text), eviction policy type (dropdown), eviction threshold (number), retry budget (number).
   - Vault dropdown for default vault — fetches vaults via a new `useVaults()` hook (call this out to T022's vault page work; or build a tiny `useVaultsList()` here and let T022 reuse it). **Decision: build `useVaultsList()` in this ticket** so the settings page works standalone; T022 will reuse the same hook.
   - Save button calls `usePatchGlobalSettings(formState)`; show success/error feedback (success toast, error inline).
   - `updated_at` shown in human-readable relative format (e.g., "saved 2 minutes ago").

4. **Write `HfCredentialSection.tsx`:**
   - Read status via `useHfCredential` (returns `{has_token, label, updated_at}`).
   - If `has_token=false`: show "No HF token set" with an "Add token" button that reveals a form (token input + optional label).
   - If `has_token=true`: show the label (or "—"), updated_at, a "Replace" button (revealing the same form with empty fields), and a "Remove" button (with a confirm dialog).
   - **Never display the token value.** The input is password-type, not echoed back from the API.
   - Submit calls PUT; remove calls DELETE.

5. **Write `SettingsPage.tsx`** — a simple page rendering both sections stacked with section headers.

6. **Add `useVaultsList.ts`** alongside the others (T022 will reuse it):
   ```ts
   export function useVaultsList() {
     return useQuery<VaultListResponse>({
       queryKey: ['vaults', 'list'],
       queryFn: () => fetchApi('/api/v1/vaults'),
       staleTime: 30_000,
     })
   }
   ```

7. **Wire the route** in `router.tsx`:
   ```tsx
   { path: '/settings', element: <SettingsPage /> },
   ```
   ... inside the auth-protected `AppLayout` tree.

8. **Update `AppLayout.tsx`** — the "Settings" link in the nav becomes a real `<NavLink to="/settings">`.

9. **Manual smoke test:**
   - Log in. Click Settings.
   - Change eviction threshold to 25, save → success message; refresh; value persists.
   - Add an HF token. Status flips to "token set." Refresh — still set. Remove → flips back.
   - Set vault dropdown to a vault (if one exists; if not, the option shows "no vaults — create one in Vaults page").
   - `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test` all exit 0.

## Acceptance Criteria

- [ ] `/settings` route renders inside the logged-in `AppLayout`.
- [ ] Global settings section shows current values fetched from `/api/v1/settings/global` and allows editing of all five fields (hot tier path, default vault, eviction policy type, eviction threshold, retry budget).
- [ ] Vault dropdown is populated from `/api/v1/vaults` via `useVaultsList`; the dropdown includes an explicit "(no default vault)" option.
- [ ] Saving global settings calls PATCH and reflects the updated values immediately (no manual refresh required).
- [ ] HF credential section shows `has_token` status with label + updated_at when set.
- [ ] HF credential token input is password-type; the token value is never displayed back after entry.
- [ ] PUT and DELETE on HF credential work with feedback (success toast, error inline).
- [ ] All API calls flow through `fetchApi` (CSRF handled automatically).
- [ ] Validation errors from the backend (e.g., invalid threshold) are surfaced inline next to the relevant field where possible; generic errors as a banner above the form.
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm test` exit 0.

## Out of Scope (for this ticket)

- Vault CRUD UI — T022.
- A reset-to-defaults button — operator can manually re-enter; no convenience action in v1.
- An HF token validity check (calling HF to verify) — backlog.
- Confirmation dialog for global-settings changes — direct save is fine for v1.

## Notes

- Keep the page boring. Two stacked sections, default form styling via Tailwind's `@tailwindcss/forms` plugin (add to `tailwind.config.ts` if not present — but only if you genuinely need it; raw Tailwind classes are fine).
- The "saved X minutes ago" relative timestamp can use a tiny inline helper or `date-fns` (~2 KB after tree-shaking). Don't add `moment.js` or large date libs.
- Surface any backend response field the type generator didn't pick up — that's a sign the API contract has drifted, and we want to catch it here.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
