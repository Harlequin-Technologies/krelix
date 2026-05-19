# T020 — Frontend auth shell + API client + types generation

**Status:** Not started
**Phase:** 3 — Vault, settings, HF credential management
**Estimated session length:** 4 hr
**Depends on:** T003, T016
**Blocks:** T021, T022, every future frontend ticket
**Maps to:** `api-contracts.md` Auth section (operator-side consumption); `auth-and-security.md` (cookie + CSRF handling).

---

## Objective

Build the operator's first-run-through-logged-in frontend shell:

1. A **typed API client** that reads CSRF cookies and echoes them on mutating verbs, handles 401 by redirecting to login, and uses TypeScript types generated from the backend's OpenAPI schema.
2. **Routes:** `/setup` (first-run admin creation), `/login`, `/` (logged-in dashboard placeholder), `/logout` action.
3. **Auth state hook** (`useCurrentUser`) backed by TanStack Query against `/api/v1/auth/me`.
4. **Logged-in layout shell** with top nav (placeholders for Settings / Vaults / Endpoints / Deployments) and a logout button.

After this lands, every subsequent frontend ticket can assume "you're inside a logged-in shell" and just add a page.

## Context

This is a foundational frontend ticket. It's larger than typical because the auth flow is genuinely cross-cutting — every API call needs CSRF, every page needs auth — and getting it right once is much cheaper than patching it ticket-by-ticket. The OpenAPI-driven type generation eliminates a class of "frontend types drifted from backend contracts" bugs that would otherwise plague the build.

## Read for context

- [`../03-technical/api-contracts.md`](../03-technical/api-contracts.md) — full Auth + Conventions sections
- [`../03-technical/auth-and-security.md`](../03-technical/auth-and-security.md) — cookie + CSRF posture
- [`T016-auth-api-endpoints.md`](T016-auth-api-endpoints.md) — backend endpoints being consumed
- [`T003-frontend-react-vite-scaffold.md`](T003-frontend-react-vite-scaffold.md) — established frontend scaffold

## Files to create

- `frontend/src/api/client.ts` — `fetchApi` wrapper with CSRF handling + error parsing
- `frontend/src/api/errors.ts` — typed `ApiError` class
- `frontend/src/api/types.ts` — re-exports from `gen/openapi.ts` (generated)
- `frontend/src/api/gen/.gitkeep` — committed; the actual generated file is gitignored OR committed (operator's call — default: **commit it** so CI doesn't need to run the backend during the frontend build)
- `frontend/src/api/gen/openapi.ts` — generated TypeScript types (committed)
- `frontend/src/auth/useCurrentUser.ts` — TanStack Query hook
- `frontend/src/auth/useLogin.ts` — mutation hook
- `frontend/src/auth/useLogout.ts` — mutation hook
- `frontend/src/auth/useSetup.ts` — mutation hook for first-run setup
- `frontend/src/pages/SetupPage.tsx`
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/pages/DashboardPage.tsx` — placeholder logged-in landing
- `frontend/src/layouts/AppLayout.tsx` — logged-in shell with nav
- `frontend/src/layouts/PublicLayout.tsx` — minimal shell for setup/login
- `frontend/src/router.tsx` — refactored with auth-aware routes
- `frontend/scripts/gen-api-types.sh` — bash helper to fetch `/openapi.json` and run `openapi-typescript`

## Files to modify

- `frontend/package.json` — add `openapi-typescript` to dev deps; add `gen:api` script: `pnpm gen:api` runs `scripts/gen-api-types.sh`
- `frontend/src/App.tsx` — DELETE (replaced by router-driven pages)
- `frontend/src/main.tsx` — verify it imports the new router (which now has multiple routes)

## Files to NOT touch

- Backend (just the OpenAPI schema is read at type-gen time; backend code unchanged)
- Anything under `docs/`

## Steps

1. **Add `openapi-typescript` to frontend dev deps:** `cd frontend && pnpm add -D openapi-typescript`.

2. **Write `frontend/scripts/gen-api-types.sh`:**
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   API_URL="${API_URL:-http://localhost:8000/openapi.json}"
   OUT="${OUT:-src/api/gen/openapi.ts}"
   echo "Fetching $API_URL → $OUT"
   pnpm exec openapi-typescript "$API_URL" -o "$OUT"
   echo "Done."
   ```
   `chmod +x frontend/scripts/gen-api-types.sh`. Add to `package.json`: `"gen:api": "./scripts/gen-api-types.sh"`.

3. **Generate types once** (with the backend running): `pnpm gen:api`. Commit `src/api/gen/openapi.ts`. **Important:** the file is committed, not gitignored — CI doesn't need to run the backend, and contributors see the contracts in PRs.

4. **Write `frontend/src/api/errors.ts`:**
   ```ts
   export class ApiError extends Error {
     constructor(
       public status: number,
       public code: string,
       message: string,
       public details?: Record<string, unknown>,
     ) {
       super(message)
       this.name = 'ApiError'
     }
   }
   ```

5. **Write `frontend/src/api/client.ts`:**
   ```ts
   import { ApiError } from './errors'

   function getCookie(name: string): string | null {
     const m = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]+)'))
     return m ? decodeURIComponent(m[2]) : null
   }

   export interface FetchOpts {
     method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
     body?: unknown
     signal?: AbortSignal
   }

   export async function fetchApi<T = unknown>(
     path: string,
     opts: FetchOpts = {},
   ): Promise<T> {
     const method = opts.method ?? 'GET'
     const headers: Record<string, string> = { Accept: 'application/json' }
     const init: RequestInit = { method, credentials: 'include', signal: opts.signal }

     if (opts.body !== undefined) {
       headers['Content-Type'] = 'application/json'
       init.body = JSON.stringify(opts.body)
     }
     if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
       const csrf = getCookie('krelix_csrf')
       if (csrf) headers['X-CSRF-Token'] = csrf
     }
     init.headers = headers

     const res = await fetch(path, init)
     if (res.status === 204) return undefined as T
     const text = await res.text()
     const data = text ? JSON.parse(text) : undefined
     if (!res.ok) {
       const err = data?.error ?? { code: 'unknown', message: res.statusText }
       throw new ApiError(res.status, err.code, err.message, err.details)
     }
     return data as T
   }
   ```

6. **Write `useCurrentUser.ts`, `useLogin.ts`, `useLogout.ts`, `useSetup.ts`** as small TanStack Query hooks. Example:
   ```ts
   // useCurrentUser.ts
   import { useQuery } from '@tanstack/react-query'
   import { fetchApi } from '../api/client'
   import type { components } from '../api/gen/openapi'

   type User = components['schemas']['UserResponse']

   export function useCurrentUser() {
     return useQuery<User | null>({
       queryKey: ['currentUser'],
       queryFn: async () => {
         try {
           return await fetchApi<User>('/api/v1/auth/me')
         } catch (e: any) {
           if (e?.status === 401) return null
           throw e
         }
       },
       staleTime: 60_000,
     })
   }
   ```

   `useLogin` calls POST `/api/v1/auth/login`, then `queryClient.invalidateQueries(['currentUser'])`. Similar pattern for `useLogout` and `useSetup`.

7. **Write `LoginPage.tsx`** — controlled form with username + password fields, calls `useLogin`, on success navigates to `/`. Error display under the form.

8. **Write `SetupPage.tsx`** — same shape, calls `useSetup`. Add password-confirmation field. Show only if `useCurrentUser` returns null AND the API returned a specific signal that setup is required — or simpler: just always show `/setup` and let the backend return 409 if already set up; show that as a friendly redirect-to-login message.

9. **Write `AppLayout.tsx`** — top nav with placeholder links (Settings, Vaults, Endpoints, Deployments) wired to routes that don't exist yet (404s fine), the operator's username in the corner, a Logout button. Wraps `<Outlet />` from React Router.

10. **Write `PublicLayout.tsx`** — minimal layout (centered card on a soft background) for `/setup` and `/login`.

11. **Refactor `router.tsx`:**
    ```tsx
    import { createBrowserRouter, Navigate } from 'react-router-dom'
    import AppLayout from './layouts/AppLayout'
    import PublicLayout from './layouts/PublicLayout'
    import DashboardPage from './pages/DashboardPage'
    import LoginPage from './pages/LoginPage'
    import SetupPage from './pages/SetupPage'
    import { RequireAuth } from './auth/RequireAuth'

    export const router = createBrowserRouter([
      {
        element: <PublicLayout />,
        children: [
          { path: '/setup', element: <SetupPage /> },
          { path: '/login', element: <LoginPage /> },
        ],
      },
      {
        element: <RequireAuth><AppLayout /></RequireAuth>,
        children: [
          { path: '/', element: <DashboardPage /> },
        ],
      },
      { path: '*', element: <Navigate to="/" replace /> },
    ])
    ```

    `RequireAuth.tsx`: if `useCurrentUser()` returns `null`, redirect to `/login`; while loading, render a spinner/skeleton.

12. **Test manually:**
    - Start dev stack (`make dev`)
    - On a fresh DB: `pnpm dev` → visit `localhost:5173/` → redirected to `/login`. Visit `/setup` → fill form → redirected to `/` showing "Welcome, admin."
    - Refresh `/` → stays logged in.
    - Click Logout → redirected to `/login`.
    - Visit `/setup` after setup is complete → API returns 409; page shows a "Setup already complete, redirecting to login" UX (frontend can detect via the error code).

## Acceptance Criteria

- [ ] `pnpm gen:api` regenerates `src/api/gen/openapi.ts` from a running backend's `/openapi.json`.
- [ ] `fetchApi` automatically attaches `X-CSRF-Token` header on mutating verbs.
- [ ] `fetchApi` parses error responses into `ApiError` (status, code, message, details).
- [ ] `useCurrentUser` returns the logged-in user or `null`; 401 is handled gracefully (returns null, not throws).
- [ ] `/setup` works end-to-end on a fresh DB and is gated to first-run.
- [ ] `/login` works end-to-end and shows error feedback on invalid creds.
- [ ] `/` requires auth; unauthenticated users redirect to `/login`.
- [ ] Logout invalidates the session in Redis and the frontend currentUser query.
- [ ] Top nav renders inside `AppLayout`; placeholder links exist for Settings, Vaults, Endpoints, Deployments.
- [ ] All TypeScript types for API calls trace back to `gen/openapi.ts` — no hand-written duplicates.
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm format:check`, `pnpm test` all exit 0.
- [ ] The dashboard at `/` includes a visible "Krelix" header and the logged-in username — no real content yet (that comes in later tickets).

## Out of Scope (for this ticket)

- Actual Settings, Vaults, Endpoints, Deployments pages — T021, T022, and later phases.
- Password change UI — backlog.
- "Remember me" toggle — sessions are already 30-day; no separate toggle.
- Theme / dark mode — not in v1.
- Internationalization — not in v1.

## Notes

- `pnpm gen:api` requires the backend to be running. Document this clearly in `frontend/README.md`.
- The generated types file (`gen/openapi.ts`) is committed — agents working on future frontend tickets shouldn't have to start the backend to compile the frontend.
- If `openapi-typescript` produces too-loose types (e.g., `unknown` everywhere), fall back to hand-typing the small set of v1 schemas — but try the generator first; it's usually clean for FastAPI-generated OpenAPI.
- Resist adding a state management library (Redux, Zustand, etc.). TanStack Query handles server state; React's `useState`/`useReducer` handle local UI state. Krelix doesn't need more.
- The `fetchApi` wrapper is intentionally tiny. If it grows beyond ~50 lines, surface it — likely we're packing too much in.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
