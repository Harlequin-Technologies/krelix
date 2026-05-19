# Agent Guidance — Krelix

Project-wide rules that every ticket inherits. **Read this before working any ticket.**

---

## Project Context

**Krelix is a self-hosted control plane for AI model operations in a homelab / multi-GPU environment.** v1 simplifies the lifecycle of discovering, downloading, and deploying HuggingFace models onto local Docker-host GPU endpoints, using vLLM as the inference engine. The product is a control-plane + per-host-agent system: the Krelix control plane (FastAPI + React + PostgreSQL + Redis on a Debian/Ubuntu VM) owns all UI, state, and orchestration; one Krelix host agent runs per registered GPU host (in container mode or systemd mode) and does all model I/O, two-tier storage management, GPU introspection, and inference-engine lifecycle.

**Stack at a glance:** Python 3.12 backend (FastAPI + SQLAlchemy 2 async + arq + asyncpg), TypeScript + React 19 frontend (Vite + Tailwind + ECharts + TanStack Query v5 + React Router v7), PostgreSQL 18, Redis 7. Auth via `pwdlib` (Argon2id) + session cookies + CSRF double-submit. Logging via `structlog`. Build tools: `uv` for Python, `pnpm` for JS. Container registry: GHCR. CI: GitHub Actions. Full detail in [`../03-technical/stack.md`](../03-technical/stack.md).

---

## How to Approach a Ticket

1. Read this file (`agent-guidance.md`)
2. Read [`definition-of-done.md`](definition-of-done.md)
3. Read the ticket itself (`TNNN-*.md`)
4. Read every file the ticket lists under **Read for context**
5. **Plan before coding.** Surface the plan if anything is unclear — do not start coding until the user confirms.
6. Implement only what the ticket asks for. Stop at the acceptance criteria.
7. When done, fill in the ticket's **Completion Summary** and report which acceptance criteria pass.

---

## When to Decide vs. Ask

**Decide on your own:**

- Function and variable naming (follow language convention)
- Internal class / module structure not specified in the ticket
- Standard library vs. small utility helpers (no new third-party deps)
- Code style within the project's lint rules
- Test names and structure
- Local helper functions inside the files you're already modifying
- Anything explicitly listed under "Decisions Deferred to Implementation" in [`../03-technical/architecture.md`](../03-technical/architecture.md)

**Ask the user before proceeding:**

- Adding any new third-party dependency (even small ones)
- Changing the data model shape (column adds/drops/renames beyond what's in the ticket)
- Changing API contract shapes (request/response fields, status codes)
- Anything in the ticket's **Out of scope** or **Files to NOT touch** lists
- Anything that contradicts the technical plan
- A library version that differs materially from the pins in [`../03-technical/stack.md`](../03-technical/stack.md) or [`../03-technical/dependencies-and-risks.md`](../03-technical/dependencies-and-risks.md)

---

## Refactoring Policy

**Do not refactor code outside the ticket's "Files to modify" list.** If you notice something worth refactoring elsewhere, leave a `# TODO(refactor): [note]` comment and mention it in the ticket's Completion Summary. Do not fix it in this ticket.

This rule is strict because Krelix is being built ticket-by-ticket by sequential agent sessions. Cross-ticket refactors break the dependency graph and cause merge conflicts.

---

## Style Rules

**Python:**

- Format: `ruff format` (replaces black)
- Lint: `ruff check`
- Type-check: `mypy` in strict mode where practical
- Naming: `snake_case` for functions/variables, `PascalCase` for classes, `SCREAMING_SNAKE` for module-level constants
- Imports: organized by `ruff` (stdlib / third-party / first-party / local)
- Async everywhere on the request path. Use `async def` for FastAPI route handlers, arq worker functions, and any function that awaits another async function.

**TypeScript:**

- Format: `prettier`
- Lint: `eslint`
- Type-check: `tsc --noEmit`
- Naming: `camelCase` for functions/variables, `PascalCase` for components/types
- React: function components only, no class components
- Imports: organized by `prettier` plugin or `eslint-plugin-import`

**Comments:**

- Explain **why**, not **what**. Don't restate what code does — the code already says that.
- Skip docstrings on obvious one-liner functions. Add them for non-obvious public functions and any function that's part of an API contract.
- Don't reference the current ticket in comments (commit messages and PR descriptions are the place for that).
- Don't add `// TODO` without a tag — use `TODO(refactor):`, `TODO(T123):`, or `TODO(operator):` so future grep'ing is meaningful.

---

## Commit Message Format

Use **Conventional Commits** with the ticket scope:

- `feat(T012): add model artifact API endpoints`
- `fix(T024): correct LRU sweep ordering on vault writes`
- `refactor(T009): extract engine config builder`
- `docs(T015): update install runbook for bare-metal agent`
- `test(T011): add tests for fit prediction edge cases`
- `chore(T001): pin uv version in CI`

One commit can cover one ticket (preferred for small tickets) or be split across multiple commits within a ticket. Each commit must compile cleanly on its own — no broken intermediate states pushed to `main`.

---

## When You Get Stuck

- If the ticket is **ambiguous**, ask the user before guessing.
- If the technical plan **contradicts itself**, surface the conflict — don't pick silently. The user routes plan-level conflicts back to the technical-architect-planner skill.
- If acceptance criteria **can't all be satisfied as written**, say so and propose a revision.
- If a library you're about to use has changed since the plan was written (broken API, removed function), surface it — do not silently swap to another library.

---

## What Never to Do

- **Never expand scope mid-ticket.** If it doesn't serve the listed acceptance criteria, it doesn't belong in this commit.
- **Never touch files outside "Files to modify" or "Files to create"** without explicit user permission. If a fix elsewhere is needed to make the ticket work, ask first.
- **Never add features that weren't requested.** "While I was in there I also added X" is the exact pattern that has burned the user twice already.
- **Never silently swap libraries or frameworks chosen in the tech plan.** If you have a strong reason to recommend a swap, surface it as a question.
- **Never bypass the auto-iteration retry budget or any other operator-configurable limit** by hardcoding around it.
- **Never log secrets** (HF tokens, passwords, session IDs, agent bearer tokens) — the structlog redaction filter exists for a reason; preserve it.
- **Never commit a `.env` file** with real values. `.env.example` lives in the repo; `.env` is gitignored.

---

## Scope Discipline (the most important rule)

The operator has been burned by scope creep twice on previous projects. This is the single biggest risk identified in [`../03-technical/dependencies-and-risks.md`](../03-technical/dependencies-and-risks.md).

Every ticket has an explicit **Out of scope** list. If a related improvement is tempting:

1. Note it as `TODO(refactor):` in a comment.
2. Add it to the ticket's Completion Summary.
3. Move on. The user will create a new ticket if it's worth doing.

**Do not** silently expand scope to "make the code cleaner" or "while I'm here." A small, finished ticket is better than a large, sprawling one.
