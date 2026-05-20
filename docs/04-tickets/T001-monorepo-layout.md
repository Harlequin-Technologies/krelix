# T001 — Monorepo layout + git config

**Status:** Done
**Phase:** 1 — Project scaffolding and dev environment
**Estimated session length:** 30 min
**Depends on:** None
**Blocks:** T002, T003, T004
**Maps to:** `tech-plan.md` Section 4 Phase 1 (scaffolding); foundational for every subsequent ticket.

---

## Objective

Establish the top-level monorepo directory layout, root `.gitignore`, root `README.md` skeleton, and `LICENSE` so that subsequent tickets have a place to land their work.

## Context

Krelix is a multi-component product (control plane + frontend + host agent + packaging assets). The repo is `github.com/Harlequin-Technologies/krelix` and is already initialized with an initial commit, README, and the `.claude/skills/` planning artifacts. This ticket adds the source-code directory structure. No code yet — just the empty skeleton with placeholder `__init__.py` / `index.ts` where needed.

## Read for context

- [`../03-technical/tech-plan.md`](../03-technical/tech-plan.md) Section 4 (build sequence)
- [`../03-technical/architecture.md`](../03-technical/architecture.md) (component breakdown)

## Files to create

- `backend/__init__.py` — empty, marks `backend/` as a Python package root (placeholder; real layout in T002)
- `backend/.gitkeep` — placeholder
- `frontend/.gitkeep` — placeholder
- `agent/.gitkeep` — placeholder
- `packaging/.gitkeep` — placeholder
- `packaging/systemd/.gitkeep` — placeholder for systemd units (T012-era)
- `docs/04-tickets/.gitkeep` — placeholder (this folder is created but not yet committed)
- `.gitignore` — top-level gitignore covering Python, Node, OS files, IDE files, env files, build outputs

## Files to modify

- `README.md` — add a "Repo Layout" section listing the directories. Keep the existing introductory content.

## Files to NOT touch

- Anything under `.claude/` — those are planning skills, not source.
- Anything under `docs/01-discovery/`, `docs/02-vision/`, `docs/03-technical/` — those are the upstream artifacts and are final.

## Steps

1. Create directories: `backend/`, `frontend/`, `agent/`, `packaging/`, `packaging/systemd/`. Add a `.gitkeep` in each.
2. Add a top-level `.gitignore` with the following sections (one block each, blank-line separated):
   - **Python:** `__pycache__/`, `*.py[cod]`, `*$py.class`, `*.egg-info/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.venv/`, `dist/`, `build/`
   - **Node:** `node_modules/`, `dist/`, `.vite/`, `*.log`, `.parcel-cache/`
   - **uv:** `.uv-cache/` (note: `uv.lock` is committed)
   - **OS:** `.DS_Store`, `Thumbs.db`, `desktop.ini`
   - **IDE:** `.idea/`, `.vscode/` (except `.vscode/settings.json` — explicitly allowed if you want to commit shared editor settings later), `*.swp`
   - **Env files:** `.env`, `.env.local`, `.env.*.local` (note: `.env.example` IS committed)
   - **Krelix runtime:** `/var/lib/krelix/` (in case anyone tries `git status` from a host with the hot tier)
3. Update `README.md` to add a section after the existing intro, titled `## Repository Layout`, listing each top-level directory with a one-line purpose. Keep prose tight.
4. Verify the layout with `find . -maxdepth 2 -type d -not -path './.git*' -not -path './.claude*'`.

## Acceptance Criteria

- [ ] `backend/`, `frontend/`, `agent/`, `packaging/`, `packaging/systemd/` directories exist with `.gitkeep` files.
- [ ] `.gitignore` exists at repo root and contains the sections listed above.
- [ ] `README.md` has a `## Repository Layout` section describing each top-level directory in one line each.
- [ ] `git status` shows no unintended files (no `__pycache__`, `.DS_Store`, etc.).
- [ ] `git ls-files` lists all created `.gitkeep` files and the new `.gitignore`.

## Out of Scope (for this ticket)

- Python project files (`pyproject.toml`, etc.) — that's T002
- Frontend `package.json` and Vite setup — that's T003
- Agent package skeleton — that's T004
- Dockerfiles — those are T005 and T006
- Compose files — that's T007
- CI — that's T008
- Any actual code

## Notes

Keep this ticket *very* small. It's just the empty skeleton. Resist the urge to scaffold any tooling here — that's why T002–T004 exist.

---

## Completion Summary

- **Files touched:**
  - Created: `.gitignore`, `backend/__init__.py`, `backend/.gitkeep`, `frontend/.gitkeep`, `agent/.gitkeep`, `packaging/.gitkeep`, `packaging/systemd/.gitkeep`
  - Modified: `README.md` (added `## Repository Layout` section), `docs/04-tickets/T001-monorepo-layout.md` (this file)
- **Deviations from the ticket (if any):**
  - Skipped creating `docs/04-tickets/.gitkeep`. The ticket lists it with the parenthetical "this folder is created but not yet committed," but the directory already exists in the working tree containing `agent-guidance.md`, `definition-of-done.md`, `000-index.md`, and all `TNNN-*.md` ticket files, so a `.gitkeep` there would have no effect. Operator confirmed skipping it during planning.
- **TODOs left for other tickets:** None.
- **Commit hashes:**
  - `690b256` — chore(T001): scaffold monorepo layout
  - `f9f0b1c` — docs(T001): record commit hash in completion summary
  - `dddb9d9` — docs(T001): backfill self-referential commit hash
