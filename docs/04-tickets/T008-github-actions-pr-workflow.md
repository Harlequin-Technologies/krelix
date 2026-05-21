# T008 — GitHub Actions PR workflow (lint + typecheck + test + image build)

**Status:** Done
**Phase:** 1 — Project scaffolding and dev environment
**Estimated session length:** 1.5 hr
**Depends on:** T005, T006
**Blocks:** Nothing in Phase 1; downstream phases rely on CI being green.
**Maps to:** `deployment.md` "CI/CD Detail" → `pr.yml` workflow.

---

## Objective

Wire the GitHub Actions PR pipeline: on every PR to `main`, run lint + format-check + type-check + unit tests for backend, frontend, and agent, and build both Docker images as smoke tests (no push). The workflow must complete in under 10 minutes on a clean cache.

## Context

CI is the first line of defense against agent-induced regressions. Every ticket from this point on relies on green CI to validate work. The pipeline must be fast enough that operators don't grow blind to it, and strict enough that real regressions are caught. The `main.yml` and `release.yml` workflows (image push + tagging) are deliberately deferred to a later ticket — we only need `pr.yml` to land first so subsequent tickets can rely on it.

## Read for context

- [`../03-technical/deployment.md`](../03-technical/deployment.md) — "CI/CD Detail" section
- [`T002-backend-python-package.md`](T002-backend-python-package.md), [`T003-frontend-react-vite-scaffold.md`](T003-frontend-react-vite-scaffold.md), [`T004-agent-python-package.md`](T004-agent-python-package.md) — the tools the workflow invokes
- [`T005-control-plane-dockerfile-fastapi-skeleton.md`](T005-control-plane-dockerfile-fastapi-skeleton.md), [`T006-agent-dockerfile.md`](T006-agent-dockerfile.md) — the Dockerfiles the workflow builds

## Files to create

- `.github/workflows/pr.yml` — the PR pipeline
- `.github/CODEOWNERS` — minimal CODEOWNERS file (so PRs route to the operator)
- `.github/pull_request_template.md` — short PR template referencing the ticket structure

## Files to modify

- Root `README.md` — add a CI status badge near the top once the workflow has run once (the badge URL comes from the rendered workflow page; agent should include the badge code with a placeholder URL and note in the Completion Summary that the URL needs to be confirmed after the first PR run)

## Files to NOT touch

- The `main.yml` and `release.yml` workflows — those are a later ticket (image push to GHCR + version tagging).
- `backend/`, `frontend/`, `agent/` source — workflow consumes them, doesn't modify them.

## Steps

1. **Write `.github/workflows/pr.yml`** with the following jobs running in parallel where possible:

   ```yaml
   name: PR
   on:
     pull_request:
       branches: [main]
   permissions:
     contents: read
   jobs:
     backend:
       runs-on: ubuntu-24.04
       steps:
         - uses: actions/checkout@v4
         - name: Install uv
           uses: astral-sh/setup-uv@v3
           with:
             enable-cache: true
         - name: Set up Python
           run: uv python install 3.12
         - name: Install backend deps
           working-directory: backend
           run: uv sync --frozen
         - name: Ruff check
           working-directory: backend
           run: uv run ruff check .
         - name: Ruff format check
           working-directory: backend
           run: uv run ruff format --check .
         - name: Mypy
           working-directory: backend
           run: uv run mypy src
         - name: Pytest
           working-directory: backend
           run: uv run pytest --cov=krelix --cov-report=term

     frontend:
       runs-on: ubuntu-24.04
       steps:
         - uses: actions/checkout@v4
         - uses: pnpm/action-setup@v4
           with:
             version: 9
         - uses: actions/setup-node@v4
           with:
             node-version: 20
             cache: pnpm
             cache-dependency-path: frontend/pnpm-lock.yaml
         - name: Install frontend deps
           working-directory: frontend
           run: pnpm install --frozen-lockfile
         - name: ESLint
           working-directory: frontend
           run: pnpm lint
         - name: Prettier check
           working-directory: frontend
           run: pnpm format:check
         - name: Typecheck
           working-directory: frontend
           run: pnpm typecheck
         - name: Vitest
           working-directory: frontend
           run: pnpm test
         - name: Build
           working-directory: frontend
           run: pnpm build

     agent:
       runs-on: ubuntu-24.04
       steps:
         - uses: actions/checkout@v4
         - name: Install uv
           uses: astral-sh/setup-uv@v3
           with:
             enable-cache: true
         - name: Set up Python
           run: uv python install 3.12
         - name: Install agent deps
           working-directory: agent
           run: uv sync --frozen
         - name: Ruff check
           working-directory: agent
           run: uv run ruff check .
         - name: Ruff format check
           working-directory: agent
           run: uv run ruff format --check .
         - name: Mypy
           working-directory: agent
           run: uv run mypy src
         - name: Pytest
           working-directory: agent
           run: uv run pytest

     docker-control:
       runs-on: ubuntu-24.04
       needs: [backend]
       steps:
         - uses: actions/checkout@v4
         - uses: docker/setup-buildx-action@v3
         - name: Build control-plane image
           uses: docker/build-push-action@v6
           with:
             context: ./backend
             push: false
             tags: krelix-control:pr-${{ github.event.pull_request.number }}
             cache-from: type=gha
             cache-to: type=gha,mode=max

     docker-agent:
       runs-on: ubuntu-24.04
       needs: [agent]
       steps:
         - uses: actions/checkout@v4
         - uses: docker/setup-buildx-action@v3
         - name: Build agent image
           uses: docker/build-push-action@v6
           with:
             context: ./agent
             push: false
             tags: krelix-agent:pr-${{ github.event.pull_request.number }}
             cache-from: type=gha
             cache-to: type=gha,mode=max
   ```

   - Five parallel jobs: `backend`, `frontend`, `agent`, `docker-control`, `docker-agent`.
   - `docker-control` depends on `backend` and `docker-agent` depends on `agent` — this keeps the dep tree clean (if Python tests fail, don't waste minutes building Docker).
   - Pin third-party action versions to a major (e.g., `@v4`) — Renovate-style updates can land in their own PRs.
   - GitHub Actions cache is used by uv (`enable-cache: true`), pnpm (`cache: pnpm`), and BuildKit (`type=gha`) — important for runtime.

2. **Write `.github/CODEOWNERS`:**
   ```
   * @<your-github-username>
   ```
   Replace with the actual operator's GitHub username (or leave a TODO if unknown; the operator can set it).

3. **Write `.github/pull_request_template.md`:**
   ```markdown
   ## Ticket
   <!-- Link to the ticket in docs/04-tickets/ -->

   ## Summary
   <!-- 1–3 sentences on what changed -->

   ## Acceptance criteria status
   <!-- Copy the ticket's acceptance criteria checklist and check what's done -->

   ## Deviations from the ticket
   <!-- "None" if none -->

   ## Out of scope
   <!-- Confirm nothing outside ticket scope changed -->
   ```

4. **Add a CI badge** to the top of the root README:
   ```markdown
   [![PR Pipeline](https://github.com/Harlequin-Technologies/krelix/actions/workflows/pr.yml/badge.svg)](https://github.com/Harlequin-Technologies/krelix/actions/workflows/pr.yml)
   ```

5. **Verify** by opening a small test PR (e.g., a trivial README edit on a feature branch):
   - All five jobs run
   - All five exit 0 (assuming earlier tickets produced clean code)
   - Total wall-clock time < 10 minutes on a cold cache; < 5 minutes on a warm cache

## Acceptance Criteria

- [ ] `.github/workflows/pr.yml` exists with the five jobs (`backend`, `frontend`, `agent`, `docker-control`, `docker-agent`).
- [ ] On a real PR, all five jobs run and exit 0 against the current `main` content.
- [ ] Each job uses caching (`uv` cache, pnpm cache, BuildKit cache) to amortize across runs.
- [ ] Pipeline wall-clock time on a warm cache is under 10 minutes; under 5 if everything caches.
- [ ] `.github/CODEOWNERS` and `.github/pull_request_template.md` exist.
- [ ] README has the CI badge.

## Out of Scope (for this ticket)

- `main.yml` (push to GHCR on main) — a later ticket once we want released images
- `release.yml` (version tagging + `:latest`) — same
- Renovate / Dependabot setup — a polish-phase concern
- Branch protection rules — operator configures these on GitHub, not the agent
- Coverage uploaders (Codecov, etc.) — not needed for v1
- Performance test jobs — not in v1 scope

## Notes

- If `astral-sh/setup-uv@v3` is no longer the current major at build time, surface it and pin to the current major.
- The `frontend` job runs `pnpm test` even though there are no tests yet — Vitest exits 0 on "no tests collected" mode. This keeps the script in place for when tests do land.
- If GitHub Actions cache misses (cold) cause timeouts, surface it — but don't lengthen the timeout silently.
- Don't add a status check requirement in the workflow itself — that's done via GitHub UI branch protection, which is operator-side.

---

## Completion Summary

- **Files touched:**
  - Created `.github/workflows/pr.yml` — five-job PR pipeline (backend, frontend, agent, docker-control, docker-agent) per the ticket's YAML, verbatim.
  - Created `.github/CODEOWNERS` — `* @brian-rodenkirk` (operator confirmed the handle).
  - Created `.github/pull_request_template.md` — verbatim from the ticket.
  - Modified `README.md` — added the PR Pipeline status badge under the H1.
- **Deviations from the ticket (if any):**
  - The ticket's YAML pinned `pnpm/action-setup@v4` to `version: 9`. The first PR run failed because pnpm 9 strictly requires a `packages:` field in `frontend/pnpm-workspace.yaml`, but that file (created in T003) uses pnpm 10+'s `allowBuilds` / `onlyBuiltDependencies` convention with no `packages:` declaration. Bumped CI to `version: 10` to match the lockfile's source and clear the install step. Approved by operator before applying.
  - The badge URL points at `Harlequin-Technologies/krelix` to match the configured git remote. The badge URL is the final form; the ticket noted it might need confirmation after the first PR run, but GitHub's badge URL scheme is deterministic from `<org>/<repo>/actions/workflows/<file>.yml`, so no follow-up should be needed.
- **TODOs left for other tickets:**
  - `main.yml` (push to GHCR on `main`) and `release.yml` (version tagging + `:latest`) — explicitly out of scope; a later ticket per [deployment.md](../03-technical/deployment.md) "CI/CD Detail".
  - Branch protection requiring all five jobs to pass before merge — operator-side GitHub UI work, not in repo.
  - Renovate / Dependabot configuration — polish-phase, not in v1.
- **Commit hashes:**
  - `60e8ea6` — chore(T008): add PR workflow, CODEOWNERS, PR template, CI badge

### Operator verification needed

The acceptance criterion "On a real PR, all five jobs run and exit 0" and the wall-clock timing criterion cannot be verified from the agent side — they require pushing this branch and opening a PR against `main`. Once that happens:

- Confirm all five jobs run and each exits 0.
- Confirm cold-cache run is under 10 min; warm-cache run is under 5 min.
- If `astral-sh/setup-uv@v3` has moved past `v3` by the time you run this, the workflow should be re-pinned to the current major.

### Acceptance criteria status

- [x] `.github/workflows/pr.yml` exists with the five jobs.
- [ ] On a real PR, all five jobs run and exit 0 — pending operator-driven PR run.
- [x] Each job uses caching (uv cache via `enable-cache: true`, pnpm cache via `cache: pnpm`, BuildKit cache via `type=gha`).
- [ ] Pipeline wall-clock under 10 min warm / 5 min fully cached — pending operator-driven PR run.
- [x] `.github/CODEOWNERS` and `.github/pull_request_template.md` exist.
- [x] README has the CI badge.
