# T057 — README + install runbooks (control plane + host agent, both modes)

**Status:** Not started
**Phase:** 13 — Release prep
**Estimated session length:** 3 hr
**Depends on:** All prior phases (everything that needs documenting must exist)
**Blocks:** T060 (release)
**Maps to:** Success criterion #7 (quietly-public release readiness — README + install steps sufficient for another technically-capable operator).

---

## Objective

Write the v1 README and four install runbooks. Every adoption attempt by another operator should succeed using these documents alone, with no recourse to the source code.

## Files to create

- `README.md` — full rewrite. Sections: What is Krelix, At a Glance, Architecture overview, Quick start (5-minute happy path), Install options, License, Roadmap, Contributing
- `docs/install/control-plane-docker.md`
- `docs/install/control-plane-bare-metal.md`
- `docs/install/host-agent-docker.md`
- `docs/install/host-agent-bare-metal.md` — extended from T055
- `CONTRIBUTING.md` — minimal: how to develop, run tests, open a PR
- `CHANGELOG.md` — initial v1.0.0 entry

## Steps

1. README.md:
   - Hero: one-paragraph pitch + GIF or screenshot of the deploy flow (animated if possible; static is fine).
   - "What is Krelix" — vision in 3 paragraphs, copied/refined from `prd.md` Section 1.
   - At a glance: bulleted list of v1 capabilities.
   - Architecture overview: one paragraph + a text-only diagram (no rendered image needed for v1).
   - Quick start: minimal commands to get the canonical MVD demo running.
   - Install options: pointers to the four runbooks.
   - Roadmap: v2/v3 phases (C, D, E from the parking lot) with calibrated dates if any.
   - License: Apache 2.0 (chosen) — commit a `LICENSE` file.
2. Control plane runbooks:
   - Docker mode: prereqs (Docker, Compose, disk, RAM), `.env` setup, `docker compose up -d`, first-run admin setup, troubleshooting common issues.
   - Bare metal: Debian/Ubuntu, system Postgres/Redis, systemd units (mirror what's in `deployment.md`), troubleshooting.
3. Host agent runbooks:
   - Docker mode: NVIDIA Container Toolkit prereq, compose snippet (referenced from the UI's install instructions), troubleshooting.
   - Bare metal: from T055/T056 — verified end-to-end.
4. CONTRIBUTING.md: dev environment, `make dev`, test commands, PR template usage, ticket structure pointer.
5. CHANGELOG.md: v1.0.0 entry summarizing the user stories shipped.

## Acceptance Criteria

- [ ] README.md is rewritten and is reasonably attractive (someone reading it for 90 seconds gets it).
- [ ] All four install runbooks exist and are independently usable.
- [ ] LICENSE file is committed (Apache 2.0).
- [ ] CONTRIBUTING.md is short but functional.
- [ ] CHANGELOG.md has an initial v1.0.0 entry listing the main capabilities.
- [ ] A spot-check: pick one runbook (e.g., control-plane Docker), follow it on a fresh VM, verify the operator can reach first-run setup in <15 minutes.

## Out of Scope

- A marketing landing page — Krelix is "quietly public," no marketing needed.
- A separate user-guide site — runbooks live in `docs/`.

---

## Completion Summary
- **Files touched:**
- **Deviations:**
- **TODOs for other tickets:**
- **Commit hashes:**
