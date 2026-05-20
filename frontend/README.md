# Krelix Frontend

React 19 + Vite + TypeScript + Tailwind single-page app for the Krelix control plane. In production it is served by the FastAPI backend; in development Vite runs on port 5173 and proxies `/api` and `/agent` requests to the backend on port 8000.

## Quick start

```bash
pnpm install
pnpm dev          # http://localhost:5173
pnpm build        # produces dist/
pnpm typecheck    # tsc --noEmit
pnpm lint         # eslint
pnpm format       # prettier --write .
pnpm format:check # prettier --check .
pnpm test         # vitest run
```
