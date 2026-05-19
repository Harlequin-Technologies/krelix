# Ticket Index — Krelix

Master list of all work tickets, dependency graph, and the prompt template for handing tickets to a coding agent.

---

## How to Work a Ticket

1. Open the ticket file (`TNNN-*.md`).
2. Use the **Agent Prompt Template** below — replace `[TICKET NUMBER]` with the ticket.
3. Paste into Claude Code / Cursor / your coding agent of choice.
4. When the agent reports done, **verify each acceptance criterion yourself** before checking the box in the Completion Checklist below.

---

## Agent Prompt Template

Copy this exactly when starting a ticket:

> Working ticket **[TICKET NUMBER]** for **Krelix**.
>
> Before starting:
> 1. Read `docs/04-tickets/agent-guidance.md`
> 2. Read `docs/04-tickets/definition-of-done.md`
> 3. Read `docs/04-tickets/[TICKET NUMBER]-*.md`
> 4. Read every file the ticket lists under **Read for context**
>
> Then plan the work and surface the plan before coding. Do not start coding until I confirm the plan. When you finish, update the ticket's Completion Summary and report which acceptance criteria pass.

---

## Project-Wide Documents

Every agent should read these before any ticket:

- [agent-guidance.md](agent-guidance.md) — project-wide rules every ticket inherits
- [definition-of-done.md](definition-of-done.md) — what "done" means everywhere
- [user-actions.md](user-actions.md) — things only the operator can do (NOT agent work)

---

## Phase Map

### Phase 1 — Project scaffolding and dev environment

Foundational repo + toolchain. ~10 hours.

| # | Title | Depends on | Status |
|---|---|---|---|
| T001 | Monorepo layout + git config | — | ☐ Not started |
| T002 | Backend Python package + uv + ruff + mypy + pytest | T001 | ☐ Not started |
| T003 | Frontend React + Vite + TypeScript + Tailwind scaffold | T001 | ☐ Not started |
| T004 | Agent Python package + uv | T001 | ☐ Not started |
| T005 | Control-plane Dockerfile + basic FastAPI app (healthz/readyz) + structlog | T002 | ☐ Not started |
| T006 | Agent Dockerfile (container-mode skeleton) | T004 | ☐ Not started |
| T007 | docker-compose.dev.yml + Makefile dev targets | T002, T003, T004 | ☐ Not started |
| T008 | GitHub Actions PR workflow | T005, T006 | ☐ Not started |

### Phase 2 — Database foundation + auth

Models, migrations, sessions, login flow. ~15 hours.

| # | Title | Depends on | Status |
|---|---|---|---|
| T009 | Settings + DB/Redis connections + /readyz wiring | T005 | ☐ Not started |
| T010 | SQLAlchemy ORM models (all entities) | T009 | ☐ Not started |
| T011 | Alembic setup + initial migration + seed migration | T009, T010 | ☐ Not started |
| T012 | Crypto utilities (HKDF + AES-256-GCM) | T009 | ☐ Not started |
| T013 | Password hashing with pwdlib (Argon2id) | T002 | ☐ Not started |
| T014 | Redis-backed session storage + auth dependency | T009 | ☐ Not started |
| T015 | CSRF middleware (double-submit) | T009 | ☐ Not started |
| T016 | Auth API (setup, login, logout, me + rate limiting) | T010, T011, T013, T014, T015 | ☐ Not started |

### Phase 3 — Vault, settings, HF credential management

CRUD + minimal UI for the configuration layer. ~14 hours.

| # | Title | Depends on | Status |
|---|---|---|---|
| T017 | Global settings API | T011, T014, T015 | ☐ Not started |
| T018 | HF credential API (encrypted) | T011, T012, T014, T015 | ☐ Not started |
| T019 | Vault CRUD API | T010, T011, T014, T015 | ☐ Not started |
| T020 | Frontend auth shell + API client + types generation | T003, T016 | ☐ Not started |
| T021 | Frontend settings page | T017, T018, T020 | ☐ Not started |
| T022 | Frontend vaults page | T019, T020 | ☐ Not started |

### Phase 4 — Endpoint registration + agent bootstrap protocol

Operator registers endpoints; agent skeleton can authenticate + connect. ~13 hours.

| # | Title | Depends on | Status |
|---|---|---|---|
| T023 | Endpoint CRUD API + resolved-config helper | T010, T011, T014, T015, T017 | ☐ Not started |
| T024 | Agent bearer-token auth + Agent registration endpoint | T010, T023 | ☐ Not started |
| T025 | Agent WebSocket stream skeleton + /agent/v1/config | T009, T024 | ☐ Not started |
| T026 | Frontend endpoint pages | T020, T023 | ☐ Not started |

### Phase 5 — Host agent skeleton (container mode)

Agent code: register, report GPUs+MIG, heartbeat, push live state. ~10 hours.

| # | Title | Depends on | Status |
|---|---|---|---|
| T027 | Agent core: config + structlog + CLI scaffold | T004 | ☐ Not started |
| T028 | Agent registration flow + GPU/MIG inventory via pynvml | T024, T027 | ☐ Not started |
| T029 | Agent WebSocket client + heartbeat + periodic GPU state push | T025, T028 | ☐ Not started |
| T030 | Control plane: route gpu_state frames + frontend live GPU display | T025, T029 | ☐ Not started |

### Phase 6 — HuggingFace browsing + fit prediction

HF search, model metadata, fit prediction, browser UI. ~11 hours.

| # | Title | Depends on | Status |
|---|---|---|---|
| T031 | HF search + model metadata API (proxy) | T018 | ☐ Not started |
| T032 | Model entity persistence + revision resolution | T031 | ☐ Not started |
| T033 | Fit prediction logic + /api/v1/fit-predictions | T030, T032 | ☐ Not started |
| T034 | Frontend HF browser + fit prediction display | T020, T031, T032, T033 | ☐ Not started |

### Phase 7 — Deployment happy path

End-to-end deploy of one model via vLLM, no iteration. ~18 hours.

| # | Title | Depends on | Status |
|---|---|---|---|
| T035 | Deployment create API + arq job enqueue | T010, T011, T023, T030, T032, T033 | ☐ Not started |
| T036 | Deployment orchestrator arq job + send deploy frame | T025, T035 | ☐ Not started |
| T037 | Agent deploy command: download + launch vLLM | T029, T036 | ☐ Not started |
| T038 | Control plane: handle deployment_status frames | T025, T037 | ☐ Not started |
| T039 | Deployment read APIs + status WS + stop endpoint | T035, T038 | ☐ Not started |
| T040 | Frontend deploy flow + deployments list + live status | T020, T034, T035, T039 | ☐ Not started |

### Phase 8 — Auto-iteration loop

Recover from common vLLM startup failures automatically. ~7 hours.

| # | Title | Depends on | Status |
|---|---|---|---|
| T041 | Failure-mode catalog + recovery strategies | T037 | ☐ Not started |
| T042 | Auto-iteration wiring: retry budget + adjustment loop | T037, T041 | ☐ Not started |
| T043 | Iteration event reporting + frontend timeline | T038, T042 | ☐ Not started |

### Phase 9 — Log streaming

Live vLLM logs from agent → operator UI via SSE. ~7 hours.

| # | Title | Depends on | Status |
|---|---|---|---|
| T044 | Agent log capture + log frames over WS | T037, T042 | ☐ Not started |
| T045 | Control plane SSE endpoint + log buffer | T038, T044 | ☐ Not started |
| T046 | Frontend log viewer with live tail | T040, T045 | ☐ Not started |

### Phase 10 — Two-tier storage + eviction

Hot ↔ vault, LRU eviction with pinning. ~8 hours.

| # | Title | Depends on | Status |
|---|---|---|---|
| T047 | Two-tier flow: hot ↔ vault + atomic rename | T037 | ☐ Not started |
| T048 | LRU eviction sweep with pinning support | T047 | ☐ Not started |
| T049 | Pin/unpin API + frontend artifact list | T026, T047 | ☐ Not started |

### Phase 11 — Frontend polish + deployment history

History view, badges, polish, endpoint detail tabs. ~8 hours.

| # | Title | Depends on | Status |
|---|---|---|---|
| T050 | Deployment history view with filters | T039, T040 | ☐ Not started |
| T051 | License + revision metadata badges | T034, T040 | ☐ Not started |
| T052 | Download progress + config override UX | T040, T044 | ☐ Not started |
| T053 | Endpoint detail polish: resolved config + tabs | T026, T030, T049 | ☐ Not started |

### Phase 12 — Bare-metal/systemd host agent path

The second supported install mode for the agent. ~7 hours.

| # | Title | Depends on | Status |
|---|---|---|---|
| T054 | vLLM subprocess engine adapter | T037, T044 | ☐ Not started |
| T055 | Systemd unit + bare-metal install runbook | T054 | ☐ Not started |
| T056 | Bare-metal install validation on real VM | T055 | ☐ Not started |

### Phase 13 — Release prep

Docs, CI, fit-prediction quality gate, v1.0 tag. ~11 hours.

| # | Title | Depends on | Status |
|---|---|---|---|
| T057 | README + install runbooks | All prior phases | ☐ Not started |
| T058 | Hand-curated 20-combo fit-prediction test set | T033, T040 | ☐ Not started |
| T059 | main.yml + release.yml CI workflows | T008 | ☐ Not started |
| T060 | MVD demo run + v1.0.0 release tag | T057, T058, T059 | ☐ Not started |

---

## Dependency Graph (text-mode summary)

```
Phase 1 (foundation):
  T001 ─┬─ T002 ─┬─ T005 ─┐
        ├─ T003 ─────────┤
        └─ T004 ─┬─ T006 ─┤
                         ├─ T007
                         └─ T008

Phase 2 (DB + auth):
  T005 ─── T009 ─┬─ T010 ─── T011 ──┐
                 ├─ T012 ──────────┤
                 ├─ T014 ──────────┤
                 ├─ T015 ──────────┤
  T002 ──────────── T013 ──────────┤
                                   └─ T016

Phase 3 (settings/vaults):
  T011 ─┬─ T017 ─┐
        ├─ T018 ─┤
        ├─ T019 ─┤   T020 (T003+T016) ──┐
                │                       │
                └────────── T021 ───────┤
                            T022 ───────┘

Phase 4 (endpoint+agent bootstrap):
  T017 ─── T023 ─┬─ T024 ─── T025
                 └─ T026 (with T020)

Phase 5 (agent skeleton):
  T004 ─── T027 ─── T028 (with T024) ─── T029 (with T025) ─── T030

Phase 6 (HF + fit prediction):
  T018 ─── T031 ─── T032 ─── T033 (with T030) ─── T034 (with T020)

Phase 7 (deploy):
  T035 ─── T036 ─── T037 ─── T038 ─── T039 ─── T040

Phase 8 (iteration):
  T037 ─── T041 ─── T042 ─── T043

Phase 9 (logs):
  T042 ─── T044 ─── T045 ─── T046

Phase 10 (storage):
  T037 ─── T047 ─┬─ T048
                 └─ T049 (with T026)

Phase 11 (polish):
  T050, T051, T052, T053 (largely parallel)

Phase 12 (bare-metal):
  T037 ─── T054 ─── T055 ─── T056

Phase 13 (release):
  T057, T058, T059 (parallel) ─── T060
```

---

## Completion Checklist

Master list — check off each ticket as you verify its acceptance criteria yourself (not just when the agent claims done).

**Phase 1 — Scaffolding (8)**
- [ ] T001 — Monorepo layout
- [ ] T002 — Backend Python package
- [ ] T003 — Frontend scaffold
- [ ] T004 — Agent Python package
- [ ] T005 — Control-plane Dockerfile + FastAPI skeleton
- [ ] T006 — Agent Dockerfile
- [ ] T007 — docker-compose.dev.yml + Makefile
- [ ] T008 — GitHub Actions PR workflow

**Phase 2 — DB + auth (8)**
- [ ] T009 — Settings + DB/Redis connections
- [ ] T010 — SQLAlchemy ORM models
- [ ] T011 — Alembic + initial migration + seed
- [ ] T012 — Crypto utilities
- [ ] T013 — Password hashing
- [ ] T014 — Redis sessions
- [ ] T015 — CSRF middleware
- [ ] T016 — Auth API

**Phase 3 — Settings/vaults (6)**
- [ ] T017 — Global settings API
- [ ] T018 — HF credential API
- [ ] T019 — Vault CRUD API
- [ ] T020 — Frontend auth shell + API client
- [ ] T021 — Frontend settings page
- [ ] T022 — Frontend vaults page

**Phase 4 — Endpoint registration (4)**
- [ ] T023 — Endpoint CRUD API + resolved-config helper
- [ ] T024 — Agent bearer-token auth + registration
- [ ] T025 — Agent WebSocket skeleton + /agent/v1/config
- [ ] T026 — Frontend endpoint pages

**Phase 5 — Host agent skeleton (4)**
- [ ] T027 — Agent core: config + CLI
- [ ] T028 — Agent registration + GPU/MIG inventory
- [ ] T029 — Agent WebSocket client + heartbeat
- [ ] T030 — gpu_state frame fanout + frontend live GPU

**Phase 6 — HF + fit prediction (4)**
- [ ] T031 — HF search + metadata API
- [ ] T032 — Model persistence + revision resolution
- [ ] T033 — Fit prediction
- [ ] T034 — Frontend HF browser

**Phase 7 — Deploy (6)**
- [ ] T035 — Deployment create API
- [ ] T036 — Deployment orchestrator job
- [ ] T037 — Agent deploy command handler
- [ ] T038 — deployment_status frame handling
- [ ] T039 — Deployment read APIs + WS
- [ ] T040 — Frontend deploy flow

**Phase 8 — Auto-iteration (3)**
- [ ] T041 — Failure-mode catalog
- [ ] T042 — Auto-iteration wiring
- [ ] T043 — Iteration events frontend

**Phase 9 — Logs (3)**
- [ ] T044 — Agent log capture
- [ ] T045 — Control plane SSE
- [ ] T046 — Frontend log viewer

**Phase 10 — Two-tier + eviction (3)**
- [ ] T047 — Two-tier flow + atomic rename
- [ ] T048 — LRU eviction with pinning
- [ ] T049 — Pin/unpin API + frontend

**Phase 11 — Polish (4)**
- [ ] T050 — Deployment history view
- [ ] T051 — License + revision badges
- [ ] T052 — Download progress + config override
- [ ] T053 — Endpoint detail polish

**Phase 12 — Bare-metal agent (3)**
- [ ] T054 — Subprocess engine adapter
- [ ] T055 — systemd unit + runbook
- [ ] T056 — Bare-metal validation

**Phase 13 — Release (4)**
- [ ] T057 — README + runbooks
- [ ] T058 — Fit-prediction test set
- [ ] T059 — main + release CI
- [ ] T060 — MVD demo + v1.0.0 release

---

## Estimated Total

**60 tickets** across 13 phases. **~140 agent-session hours** of work.

At 40 hrs/week with 100% agent throughput (unrealistic), that's ~3.5 weeks. Realistic estimate factoring operator review time, blockers, and the unknowable rate at which scope creep tries to sneak in: **4–8 weeks** of build time.

The single biggest risk is scope creep during agent build — see [`../03-technical/dependencies-and-risks.md`](../03-technical/dependencies-and-risks.md). Every ticket has explicit Out of Scope and Files to NOT touch lists. **Use them.**

---

## User-Required Actions

See [user-actions.md](user-actions.md) for things the operator must do alongside agent work. Some are gated by specific phases — review before starting each phase.
