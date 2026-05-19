# T002 — Backend Python package + uv + ruff + mypy + pytest

**Status:** Not started
**Phase:** 1 — Project scaffolding and dev environment
**Estimated session length:** 1.5 hr
**Depends on:** T001
**Blocks:** T005, T007, T008
**Maps to:** `stack.md` (Python 3.12, uv, FastAPI, SQLAlchemy 2 async, ruff, mypy, pytest); `tech-plan.md` Section 4 Phase 1.

---

## Objective

Set up the `backend/` directory as a self-contained Python package using `uv`, with `pyproject.toml`, all v1 production and dev dependencies pinned, ruff + mypy + pytest configured, and an importable empty `krelix` package. No application code yet — this ticket establishes the toolchain.

## Context

`uv` (Astral) is the chosen Python package manager. It replaces pip + pip-tools + virtualenv. The `backend/` directory will contain the FastAPI control plane and arq worker. All production dependencies from [`../03-technical/stack.md`](../03-technical/stack.md) "Key Libraries" are pinned here; the agent package (`agent/`) gets its own separate `pyproject.toml` in T004 because it has a different dependency set (no FastAPI / SQLAlchemy; yes `pynvml` / `docker-py`).

## Read for context

- [`../03-technical/stack.md`](../03-technical/stack.md) — the library audit table is the dep list
- [`../03-technical/dependencies-and-risks.md`](../03-technical/dependencies-and-risks.md) — version-currency notes (arq maintenance-only, pwdlib replaces passlib)
- [`agent-guidance.md`](agent-guidance.md) — style rules (ruff format, ruff check, mypy strict where practical)

## Files to create

- `backend/pyproject.toml` — package metadata, dependencies, tool configuration
- `backend/src/krelix/__init__.py` — empty (with `__version__ = "0.0.1"` at minimum)
- `backend/src/krelix/py.typed` — marker file for PEP 561 (mypy will inspect our types)
- `backend/tests/__init__.py` — empty
- `backend/tests/test_smoke.py` — single trivial test (`def test_import(): import krelix; assert krelix.__version__`) so pytest has something to run
- `backend/README.md` — one-paragraph "this is the Krelix control plane backend; see top-level README for product info"

## Files to modify

- `backend/.gitkeep` — DELETE (no longer needed once `src/` is populated)
- Root `.gitignore` — add `backend/.venv/`, `backend/uv.lock` is committed (don't ignore it). Verify the lockfile path.

## Files to NOT touch

- Anything outside `backend/` (frontend, agent, packaging are separate tickets).
- `docs/`, `.claude/` — not source.

## Steps

1. **Initialize the backend package with uv.** From the repo root, `cd backend && uv init --package --name krelix --python 3.12`. This creates a `pyproject.toml` and a `src/krelix/` layout. Adjust if uv's default layout differs from PEP 621-style.

2. **Edit `backend/pyproject.toml`** to set:
   - `requires-python = ">=3.12,<3.13"` (pin to 3.12 series for v1)
   - Project metadata: name `krelix`, version `0.0.1`, description, MIT-or-Apache license stub
   - `[tool.uv]` section if needed

3. **Add production dependencies** (use `uv add <pkg>` so the lockfile updates):
   - `fastapi`
   - `uvicorn[standard]`
   - `pydantic` (v2; FastAPI pulls it but pin explicitly)
   - `pydantic-settings` (env-var config)
   - `sqlalchemy[asyncio]` (v2)
   - `alembic`
   - `asyncpg`
   - `arq`
   - `redis` (the modern `redis-py`)
   - `huggingface-hub` (PyPI name has a hyphen; import name `huggingface_hub`)
   - `httpx`
   - `pwdlib[argon2]` (provides `pwdlib` + `argon2-cffi` backend)
   - `python-multipart` (FastAPI form support — needed for any future file upload; harmless to include now)
   - `structlog`
   - `cryptography` (for AES-256-GCM HF token encryption)
   - `itsdangerous` (signed cookies / HKDF utilities)

4. **Add dev dependencies** with `uv add --dev <pkg>`:
   - `ruff`
   - `mypy`
   - `pytest`
   - `pytest-asyncio`
   - `pytest-cov`
   - `httpx` (already prod; pytest-asyncio uses it for ASGI test client too — already added)
   - `asgi-lifespan` (for testing FastAPI lifespans)
   - `types-redis` (mypy stubs if redis-py doesn't ship them)

5. **Configure ruff in `pyproject.toml`:**
   ```toml
   [tool.ruff]
   line-length = 100
   target-version = "py312"

   [tool.ruff.lint]
   select = ["E", "F", "I", "B", "UP", "N", "S", "A", "C4", "T20", "RUF"]
   ignore = ["E501"]  # line length enforced by formatter

   [tool.ruff.lint.per-file-ignores]
   "tests/**" = ["S101"]  # assert in tests is fine
   ```

6. **Configure mypy in `pyproject.toml`:**
   ```toml
   [tool.mypy]
   python_version = "3.12"
   strict = true
   warn_unused_ignores = true
   warn_redundant_casts = true
   plugins = ["pydantic.mypy"]

   [[tool.mypy.overrides]]
   module = ["arq.*", "pwdlib.*"]
   ignore_missing_imports = true
   ```

7. **Configure pytest in `pyproject.toml`:**
   ```toml
   [tool.pytest.ini_options]
   asyncio_mode = "auto"
   testpaths = ["tests"]
   ```

8. **Create the trivial smoke test** in `backend/tests/test_smoke.py`:
   ```python
   import krelix

   def test_version_present() -> None:
       assert krelix.__version__
   ```

9. **Verify the toolchain works:**
   - `cd backend && uv sync` (creates `.venv` and installs)
   - `uv run ruff check .` clean
   - `uv run ruff format --check .` clean
   - `uv run mypy src` clean
   - `uv run pytest` green (1 test)

10. **Write `backend/README.md`** with one paragraph plus a "Quick start" section listing the four commands above.

## Acceptance Criteria

- [ ] `backend/pyproject.toml` exists with all production and dev dependencies listed above.
- [ ] `backend/uv.lock` exists and is committed.
- [ ] `cd backend && uv sync` succeeds on a fresh clone (no manual pip installs needed).
- [ ] `uv run ruff check .` exits 0 with no errors.
- [ ] `uv run ruff format --check .` exits 0.
- [ ] `uv run mypy src` exits 0.
- [ ] `uv run pytest` reports 1 test passed.
- [ ] `backend/src/krelix/__init__.py` contains `__version__ = "0.0.1"`.
- [ ] All Python license values in the dep tree are MIT / BSD / Apache 2.0 / PostgreSQL License (spot-check the audit in `stack.md`).

## Out of Scope (for this ticket)

- Any application code — FastAPI app, models, routes, auth, all later phases
- Dockerfile — T005
- docker-compose files — T007
- GitHub Actions — T008
- The agent package — T004 has its own `pyproject.toml`
- Adding the optional `procrastinate` or `dramatiq` fallbacks mentioned in `dependencies-and-risks.md` — those are only added if arq actually breaks

## Notes

- If `uv add huggingface-hub` resolves to a much newer or older version than expected, surface it. Major-version drift in the HF lib could affect downstream tickets.
- `pwdlib[argon2]` should pull `argon2-cffi` transitively. Verify both are in the lockfile.
- The `src/` layout (`backend/src/krelix/`) is intentional — it avoids accidental imports from the project root during tests and matches PEP 621 modern best practice.

---

## Completion Summary

- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
