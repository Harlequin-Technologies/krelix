# T004 — Agent Python package + uv

**Status:** Done
**Phase:** 1 — Project scaffolding and dev environment
**Estimated session length:** 45 min
**Depends on:** T001
**Blocks:** T006, T007
**Maps to:** `stack.md` (host agent's library set: pynvml, docker-py, structlog, httpx, websockets); `architecture.md` Component 5 (Krelix Host Agent); `tech-plan.md` Section 4 Phase 1.

---

## Objective

Set up `agent/` as a self-contained Python package using `uv`, separate from `backend/`. Different dependency set (no FastAPI / SQLAlchemy; yes pynvml / docker-py / websockets). Same toolchain (ruff + mypy + pytest). No application code — just the empty `krelix_agent` package.

## Context

The host agent runs on each GPU host, separate from the control plane. It has a small, focused dependency set: HTTP/WebSocket client (httpx, websockets), GPU introspection (pynvml), Docker client (docker-py — only used in container mode), `huggingface_hub` for downloads, structured logging. It explicitly does NOT depend on FastAPI / SQLAlchemy / Alembic. Keeping the packages separate keeps the agent Docker image small and reduces install surface.

## Read for context

- [`../03-technical/architecture.md`](../03-technical/architecture.md) — Component 5 (Host Agent) responsibilities and talks-to
- [`../03-technical/stack.md`](../03-technical/stack.md) — library audit (filter for agent-relevant libs)
- [`agent-guidance.md`](agent-guidance.md) — style rules
- [`T002-backend-python-package.md`](T002-backend-python-package.md) — companion ticket; same toolchain pattern

## Files to create

- `agent/pyproject.toml`
- `agent/src/krelix_agent/__init__.py` — empty with `__version__ = "0.0.1"`
- `agent/src/krelix_agent/py.typed`
- `agent/tests/__init__.py`
- `agent/tests/test_smoke.py` — single import test, mirrors T002 pattern
- `agent/README.md` — one paragraph + Quick start

## Files to modify

- `agent/.gitkeep` — DELETE
- Root `.gitignore` — verify `agent/.venv/` and similar caches are covered (they should be from T001)

## Files to NOT touch

- `backend/`, `frontend/`, `packaging/` — separate tickets
- Anything under `docs/` or `.claude/`

## Steps

1. `cd agent && uv init --package --name krelix-agent --python 3.12`. Adjust to a `src/` layout if uv's default differs.

2. **Edit `agent/pyproject.toml`** with `requires-python = ">=3.12,<3.13"` and project metadata.

3. **Add production dependencies** with `uv add`:
   - `huggingface-hub`
   - `pynvml` (NVIDIA NVML bindings)
   - `docker` (the docker-py package; PyPI name is `docker`)
   - `httpx`
   - `websockets` (the client lib for the persistent stream back to control plane)
   - `structlog`
   - `pydantic` (for typed config + frame validation)
   - `pydantic-settings`
   - `typer` or `click` for the agent CLI entrypoint — pick `typer` (built on click, better typing)

4. **Add dev dependencies** with `uv add --dev`:
   - `ruff`
   - `mypy`
   - `pytest`
   - `pytest-asyncio`
   - `pytest-cov`

5. **Mirror the ruff / mypy / pytest configuration** from T002's `pyproject.toml`. Adjust the package name in the mypy override list as needed.

6. **Smoke test in `agent/tests/test_smoke.py`:**
   ```python
   import krelix_agent

   def test_version_present() -> None:
       assert krelix_agent.__version__
   ```

7. **Add a stub CLI entry point** (Typer app) at `agent/src/krelix_agent/cli.py` that does nothing but print the version:
   ```python
   import typer

   from krelix_agent import __version__

   app = typer.Typer()

   @app.command()
   def version() -> None:
       """Print the agent version."""
       typer.echo(__version__)

   if __name__ == "__main__":
       app()
   ```
   And expose it as a script in `pyproject.toml`:
   ```toml
   [project.scripts]
   krelix-agent = "krelix_agent.cli:app"
   ```

8. **Verify:**
   - `cd agent && uv sync`
   - `uv run ruff check .` and `uv run ruff format --check .` clean
   - `uv run mypy src` clean
   - `uv run pytest` green
   - `uv run krelix-agent version` prints `0.0.1`

9. **Write `agent/README.md`** with one paragraph + Quick start.

## Acceptance Criteria

- [ ] `agent/pyproject.toml` exists with all dependencies listed above.
- [ ] `agent/uv.lock` exists and is committed.
- [ ] `cd agent && uv sync` succeeds on a fresh clone.
- [ ] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` all exit 0.
- [ ] `uv run krelix-agent version` prints `0.0.1` and exits 0.
- [ ] `agent/src/krelix_agent/__init__.py` contains `__version__ = "0.0.1"`.
- [ ] No FastAPI / SQLAlchemy / Alembic / asyncpg in the agent dep tree (those belong to backend only).
- [ ] All dep licenses are MIT / BSD / Apache 2.0 / PostgreSQL License.

## Out of Scope (for this ticket)

- Any actual agent logic — GPU inventory, downloads, vLLM management, WebSocket protocol — all later phases (T011-era and beyond)
- The bare-metal subprocess engine launcher — Phase 12
- Dockerfile for the agent — T006
- systemd unit — Phase 12
- Wiring the agent into docker-compose — T007

## Notes

- `pynvml` requires the NVIDIA driver / NVML library to be present at runtime, but not at install time. `uv add pynvml` will succeed on a machine without NVIDIA GPUs. The agent's actual GPU discovery code (Phase 5) will need to handle the "no NVIDIA driver present" case gracefully.
- `docker-py` is only used in container-mode agents. Bare-metal-mode agents (Phase 12) won't import it. Importing it conditionally is a Phase-12 concern.
- Resist the urge to add `fastapi-cli`, `rich`, or any UI library to the agent. The agent is a daemon — no human-facing UI.

---

## Completion Summary

- **Files touched:**
  - Created: `agent/pyproject.toml`, `agent/uv.lock`, `agent/.python-version`, `agent/README.md`, `agent/src/krelix_agent/__init__.py`, `agent/src/krelix_agent/py.typed`, `agent/src/krelix_agent/cli.py`, `agent/tests/__init__.py`, `agent/tests/test_smoke.py`
  - Deleted: `agent/.gitkeep`
  - Root `.gitignore` already covered `.venv/` and the cache dirs from T001 — no edit needed.
- **Deviations from the ticket (if any):**
  - The ticket snippet for `cli.py` used a bare `typer.Typer()` with one `@app.command()`. Typer collapses single-command apps to the root, so `krelix-agent version` (the literal acceptance-criterion invocation) was rejected with "unexpected extra argument (version)". Added an empty `@app.callback()` and `no_args_is_help=True` so `version` stays a named subcommand and the AC's exact invocation works. Behavior of `version` itself is unchanged from the spec.
- **TODOs left for other tickets:**
  - None. Ticket scope was self-contained scaffolding.
- **Commit hashes:**
  - `0f545c0` — `feat(T004): scaffold agent python package with uv toolchain`
  - (this commit) — `docs(T004): record commit hash in completion summary`

### Verification (run from `agent/`)

- `uv sync` — resolved 51 packages, clean.
- `uv run ruff check .` — All checks passed!
- `uv run ruff format --check .` — 4 files already formatted.
- `uv run mypy src` — Success: no issues found in 2 source files.
- `uv run pytest` — 1 passed.
- `uv run krelix-agent version` — `0.0.1`.
- `grep -iE '^name = "(fastapi|sqlalchemy|alembic|asyncpg|arq)"' uv.lock` — no matches (forbidden backend libs absent from agent dep tree).
- Spot-check of all 14 prod + dev dep licenses via `importlib.metadata` — all MIT, BSD-3-Clause, or Apache-2.0.

### Acceptance criteria status

- [x] `agent/pyproject.toml` exists with all dependencies listed in the ticket.
- [x] `agent/uv.lock` exists and is committed.
- [x] `cd agent && uv sync` succeeds.
- [x] `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest` all exit 0.
- [x] `uv run krelix-agent version` prints `0.0.1` and exits 0.
- [x] `agent/src/krelix_agent/__init__.py` contains `__version__ = "0.0.1"`.
- [x] No FastAPI / SQLAlchemy / Alembic / asyncpg in the agent dep tree.
- [x] All dep licenses are MIT / BSD / Apache 2.0.
