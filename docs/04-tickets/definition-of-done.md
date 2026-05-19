# Definition of Done — Krelix

A ticket is **done** only when ALL of these are true. If any item is false, the ticket is not done. Do not mark done prematurely.

---

## Code

1. **All acceptance criteria listed in the ticket are met and observable.** Each criterion must be checkable by running the code, hitting an endpoint, or reading a file — not by interpretation.
2. **Code compiles, runs, and starts without errors.**
   - Python: `uv run python -c "import <new_module>"` succeeds; the relevant entrypoint (`krelix-api`, `krelix-worker`, agent) starts without traceback.
   - TypeScript: `pnpm build` succeeds; `pnpm dev` serves without console errors at startup.
3. **Linting passes.**
   - Python: `uv run ruff check .` and `uv run ruff format --check .` are both clean.
   - TypeScript: `pnpm lint` is clean.
4. **Type-checking passes.**
   - Python: `uv run mypy <changed-package>` is clean.
   - TypeScript: `pnpm typecheck` (or `tsc --noEmit`) is clean.
5. **Tests pass.** Tests are required for backend logic with branching behavior (auth, fit prediction, auto-iteration, eviction). UI presentation-only tickets may skip unit tests but must include at least one runnable smoke check (e.g., the page renders without errors).
   - Python: `uv run pytest` is green for tests under or near the changed code. New tests are added for new branching logic.
   - TypeScript: `pnpm test` is green; new component logic with branches has at least one test.
6. **Files listed under "Files to NOT touch" were not modified.** Run `git diff --name-only origin/main` to verify.

## Hygiene

7. **No `TODO(this-ticket):` markers remain in the changed code.** TODOs for *other* tickets, refactors, or operator action are fine and should be left intact.
8. **No secrets, real credentials, or `.env` values committed.** Check `git diff` for accidental inclusions.
9. **No new third-party dependencies added without explicit user approval.** If a new dep was approved, it appears in `pyproject.toml` / `package.json` AND the lockfile (`uv.lock` / `pnpm-lock.yaml`) is updated.
10. **Commit messages follow the Conventional Commits format** specified in [`agent-guidance.md`](agent-guidance.md). Each commit on its own compiles cleanly.

## Ticket Hygiene

11. **The ticket's "Status" line is updated to `Done`.**
12. **The ticket's Completion Summary is filled in** with:
    - Files touched (full list)
    - Any deviations from the ticket, with rationale
    - TODOs left for other tickets (with their tags)
    - Commit hashes (`git log --oneline <branch>..HEAD`)
13. **Any deviations are surfaced to the user, not silently absorbed.**

## Definition-of-Done Exceptions

The following tickets have known scoped exceptions:

- **Scaffolding-only tickets (e.g., T001 monorepo layout):** no behavior to test; the acceptance criterion is "the layout exists and `make dev` runs without error."
- **Docs-only tickets (e.g., README updates):** no compile/lint required beyond markdown rendering.
- **Migration tickets:** `pytest` may not be applicable for migration code itself; the criterion is `alembic upgrade head` on a fresh DB completes and `alembic downgrade -1` reverses cleanly (where downgrades are supported).

Exceptions are stated **on the ticket** under a "Definition-of-Done exceptions" subsection. If the ticket doesn't list exceptions, the full DoD applies.
