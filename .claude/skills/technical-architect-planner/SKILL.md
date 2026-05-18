---
name: technical-architect-planner
description: Produce an opinionated, agent-ready technical plan from completed product vision artifacts — stack selection, system architecture, data model, API contracts, auth/security, deployment, dependencies, and risks. Use this skill immediately after the product-vision-synthesizer has produced the vision artifacts in `docs/02-vision/`, or whenever the user says "plan the technical side," "pick the stack," "architect this," "design the system," "I have the PRD, what do I build with," or "produce the tech plan." Also trigger when the user has a PRD/vision in hand and is asking how to actually build it. This is the third skill in a four-phase product-build pipeline — it explicitly does NOT write code or produce agent work tickets (those belong to the next skill, `agent-work-breakdown`). Use this skill any time the work involves turning product requirements into concrete technical decisions an AI coding agent could follow.
---

# Technical Architect Planner

## Purpose

This skill turns the vision artifacts from `product-vision-synthesizer` into a concrete, opinionated technical plan. The plan must be explicit enough that an AI coding agent can build from it without needing to invent decisions on the fly.

The user is a non-engineer building with AI coding agents. **Do not present buffet-style choices** ("you could use Postgres or MySQL or SQLite"). Make one well-justified pick per decision, tied to the constraints in the vision artifacts. The user can override any pick — but the default mode is "one strong recommendation, here's why."

## What This Skill Is and Is Not

**This skill IS:**
- A pass from "what" to "how": stack, architecture, data shape, API surface, deployment target
- Opinionated and decisive
- Aggressively right-sized — preferring boring, well-understood tools over novel ones
- Aware that AI coding agents will build from this — favor stacks the agents handle well

**This skill is NOT:**
- A place for new product features (that's the vision phase)
- A place to write code (that's the agents' job, driven by skill #4)
- A place to produce work tickets (that's skill #4, `agent-work-breakdown`)
- A buffet of options — make picks, justify them, let the user override

## Setup (do this first)

Before any technical work, establish:

1. **Vision artifact location.** Default: `./docs/02-vision/`. Confirm with the user and read all five files:
   - `prd.md`
   - `personas.md`
   - `user-stories.md`
   - `scope.md`
   - `success-metrics.md`

2. **Technical artifact destination.** Default: `./docs/03-technical/`. Confirm and create.

3. **Vision sufficiency check.** Before planning, verify the vision is substantive enough to plan from. See "Vision Sufficiency Check" below.

## Vision Sufficiency Check

Vision artifacts are sufficient to plan from only if **all** of these are true:

- `prd.md` is filled in with overview, problem, functional requirements (Section 5), non-functional requirements (Section 6), constraints (Section 7)
- `user-stories.md` has at least 3 Must-Have stories with acceptance criteria
- `scope.md` has explicit in-scope and out-of-scope sections populated
- Constraints in PRD Section 7 are concrete (deadline, budget, hosting/infra preferences, legal)

If anything fails, stop and tell the user:

> "Before I plan, the vision is thin in these areas: [list]. Recommend going back to `product-vision-synthesizer` to fill these in. Want me to proceed anyway with explicit `[GAP — assumption made]` callouts, or fix the vision first?"

## User Preferences (batched, before any picks)

Before making any technical recommendations, ask the user a small batched message of preference questions. These are the only things that shouldn't be inferred from the vision artifacts. Cap at 5–6 questions:

1. **Preferred languages / frameworks (if any).** "Any languages or frameworks you'd prefer or want to avoid? If none, I'll pick based on the constraints."
2. **Existing infrastructure to use.** "Any existing infrastructure I should plan around? (Homelab, existing servers, existing accounts at hosting providers, internal AI inference, existing databases, etc.)"
3. **Deployment target.** "Where should this run? (Cloud provider, VPS, homelab, end-user device, can't-decide-pick-for-me, etc.)"
4. **Public vs. private.** "Is this internet-public, internal-only, or something else?"
5. **Skill level with agent-driven coding.** "How comfortable are you reviewing agent-produced code? This affects how prescriptive I make the plan."
6. **Anything off-limits.** "Any technologies, vendors, or licenses you want to avoid (e.g., AGPL, specific cloud providers, paid services)?"

Wait for answers. Then proceed.

## Principles for Technical Decisions

Apply these in order when making each pick:

1. **Respect explicit constraints.** If PRD says "free or low cost," eliminate paid options. If user said "must run in my homelab," eliminate cloud-only. If discovery flagged sensitive data, eliminate options with poor data isolation.

2. **Right-size aggressively.** Default to the simplest, most boring, most well-documented stack that satisfies requirements. v1 CRUD apps do not need microservices, GraphQL, Kubernetes, or event sourcing. If you're tempted to recommend something complex, double-check that the requirements actually demand it.

3. **Favor agent-friendly stacks.** AI coding agents produce better, more predictable output for popular, well-documented frameworks (FastAPI, Flask, Next.js, plain HTML/CSS/JS, Django, Rails, Express) than for niche or rapidly-changing ones. Exotic choices need clear justification.

4. **Reuse existing infra when sensible.** If the user has homelab, internal AI inference, existing databases, or other infrastructure that fits, default to using it. Don't reflexively spin up new cloud resources.

5. **Surface conflicts.** If constraints contradict ("free hosting" + "needs GPU inference at scale"), name the conflict explicitly and ask the user to resolve it before picking.

6. **One pick per decision.** Make a single recommendation per choice (language, framework, DB, hosting, etc.). Give 1–3 sentences of rationale tied to constraints. Note one alternative in parentheses if it was a close call.

7. **Flag user-required decisions explicitly.** Some decisions genuinely require the user (domain name, paid service signups, account creation). Mark these clearly so they don't slip through.

## Artifact Production Order

Produce artifacts in this order. **Present each one to the user before moving to the next.** After presenting, ask: "Any changes before I move on?"

The order matters: each artifact builds on the previous.

1. **`stack.md`** — Foundational decisions everything else depends on
2. **`architecture.md`** — How the system is structured given the stack
3. **`data-model.md`** — The data the system manages
4. **`api-contracts.md`** — How clients talk to the system
5. **`auth-and-security.md`** — Trust boundaries, secrets, threats
6. **`deployment.md`** — How it gets to production and stays running
7. **`dependencies-and-risks.md`** — Third-party things and what could go wrong
8. **`tech-plan.md`** — Master consolidated doc that points to all of the above

## Artifact Templates

Use these exact templates and section headers. Skill #4 parses this structure.

### `stack.md`

```markdown
# Stack — [Project Working Title]

## Language(s)
**Pick:** [Language and version]
**Rationale:** [1–3 sentences, tied to constraints/agent-friendliness]
**Alternative considered:** [If any]

## Backend Framework
**Pick:** [Framework and version]
**Rationale:** [...]

## Frontend
**Pick:** [Approach — e.g., "Static HTML/CSS/JS, no framework" or "Next.js" or "None — API-only"]
**Rationale:** [...]

## Database
**Pick:** [DB and version]
**Rationale:** [...]
**Location:** [Where it lives — file path on homelab, managed service, etc.]

## Key Libraries
- **[Library]** — [Purpose] — [Why this one]
- **[Library]** — [Purpose] — [Why this one]

## Build / Package Management
**Pick:** [pip / uv / npm / pnpm / etc.]
**Rationale:** [...]

## Local Development
[How the user runs this locally — one paragraph]
```

### `architecture.md`

```markdown
# Architecture — [Project Working Title]

## System Overview
[One paragraph: what are the major pieces and how do they talk to each other? Describe in plain language. No box-and-arrow diagrams (text only).]

## Components
### [Component 1, e.g., "Web frontend"]
- **Responsibility:** [What this component is responsible for]
- **Talks to:** [Other components and how — HTTP, file read, etc.]
- **Does not:** [What this component is NOT responsible for, to prevent drift]

### [Component 2]
- ...

## Data Flow
[Walk through 1–2 representative user actions end-to-end: "User clicks X → frontend sends request to Y → backend does Z → returns to frontend → user sees W."]

## Trust Boundaries
[Where does untrusted input enter the system? Where is data trusted vs. validated?]

## Decisions Deferred to Implementation
[Things that don't need to be decided at this level — e.g., specific function signatures, internal class structure. List them so the agents know they have latitude.]
```

### `data-model.md`

```markdown
# Data Model — [Project Working Title]

## Entities

### [Entity name, e.g., "Employee"]
**Purpose:** [What this entity represents in the domain]

**Fields:**
| Name | Type | Constraints | Notes |
|------|------|-------------|-------|
| id | INTEGER PRIMARY KEY | NOT NULL | autoincrement |
| name | TEXT | NOT NULL | |
| salary | REAL | NOT NULL | annualized USD |
| ... | ... | ... | ... |

**Indexes:**
- [Index on what columns, why]

**Relationships:**
- [This entity relates to X via Y]

---

### [Entity 2]
...

## Migrations

[How are schema changes handled? Migration tool, file location, naming convention. Even for v1, agents need to know.]

## Seed Data

[If any — e.g., reference data, initial admin user — describe what gets seeded and from where.]
```

The data model must be concrete enough that agents can write migrations directly. Field names, types, and constraints are not optional.

### `api-contracts.md`

```markdown
# API Contracts — [Project Working Title]

## Conventions
- **Base path:** [e.g., `/api/v1`]
- **Authentication:** [How auth is presented — header, cookie, etc.]
- **Content type:** [application/json by default]
- **Error format:** [Shape of error responses — e.g., `{ "error": "...", "code": "..." }`]
- **Status codes:** [Which codes are used and when — 200, 201, 400, 401, 403, 404, 500]

## Endpoints

### [Capability, e.g., "Search employees"]
**Method:** GET
**Path:** `/api/v1/employees`
**Query parameters:**
| Name | Type | Required | Notes |
|------|------|----------|-------|
| q | string | no | search term |
| limit | int | no | default 25, max 100 |

**Response (200):**
```json
{
  "results": [
    { "id": 1, "name": "...", "salary": 12345.67 }
  ],
  "total": 42
}
```

**Errors:**
- 400 — invalid query parameter
- 500 — server error

**Maps to user stories:** US-M-01, US-M-02

---

### [Next endpoint]
...
```

Every endpoint must have method, path, params, response shape, error cases, and a back-reference to the user story it serves. If an endpoint doesn't map to a story, it shouldn't exist.

### `auth-and-security.md`

```markdown
# Auth and Security — [Project Working Title]

## Authentication
**Approach:** [None / session cookies / JWT / OAuth / API keys / etc.]
**Rationale:** [Why this fits the product — public-read site vs. multi-user app vs. internal tool]
**Implementation details:** [Library, token lifetime, refresh approach]

## Authorization
**Roles / permissions:** [If multi-user: what roles exist and what each can do]
**If single-user / public-read:** [Note that and move on]

## Secrets Management
**Where secrets live:** [.env file, secrets manager, etc.]
**What counts as a secret:** [API keys, DB credentials, session signing keys, etc.]
**Rotation strategy:** [If applicable]

## Sensitive Data
[From PRD non-functional requirements — any PII, financial data, public records nuances, etc. How is each protected?]

## Threat Model (basic)
| Threat | Likelihood | Impact | Mitigation |
|--------|-----------|--------|------------|
| [Threat 1] | [low/med/high] | [low/med/high] | [Mitigation] |
| ... | ... | ... | ... |

Cover at minimum: input validation, SQL injection / ORM safety, XSS, CSRF (if applicable), rate limiting, secrets exposure, dependency vulnerabilities.

## Compliance / Legal Notes
[Anything called out in discovery or PRD — public records, data retention, terms of use, etc.]
```

### `deployment.md`

```markdown
# Deployment — [Project Working Title]

## Target Environment
**Production runs on:** [Specific host / service / device]
**Rationale:** [Why here]

## Environments
- **Local dev:** [How the user runs it locally]
- **Staging (if any):** [Or "no staging — single environment"]
- **Production:** [Where, how accessed]

## Build & Deploy Process
[Step-by-step at a high level — e.g., "Push to main → CI runs tests → builds container → pushes to registry → server pulls latest." Or if simpler: "Pull from git, restart service."]

## CI/CD
**Pick:** [GitHub Actions / Gitea Actions / none-just-manual / etc.]
**What runs on push:** [Tests, linting, build, deploy steps]

## Domain / DNS
[If applicable — domain name, DNS provider, certificate strategy (Let's Encrypt, Caddy auto-TLS, etc.)]

## Monitoring & Logs
[Minimum viable monitoring for v1 — even just "logs to stdout, captured by systemd" counts. Don't over-specify.]

## Backup & Recovery
[For anything stateful — what's backed up, where, how often]

## User-Required Actions
Decisions and actions the user (not the agent) must perform:
- [Action 1, e.g., "Buy domain name"]
- [Action 2, e.g., "Create account at hosting provider"]
- [Action 3, e.g., "Add DNS records pointing to..."]
```

### `dependencies-and-risks.md`

```markdown
# Dependencies and Risks — [Project Working Title]

## Third-Party Services
| Service | Purpose | Cost | License/Terms concerns | Alternative if it fails |
|---------|---------|------|------------------------|------------------------|
| [Service 1] | [What it does for us] | [$ or free] | [Anything to watch] | [Fallback] |
| ... | ... | ... | ... | ... |

## Key Library Dependencies
[Anything load-bearing that isn't a standard framework piece. e.g., a specific OCR library, a payments library, etc.]

| Library | Purpose | License | Risk |
|---------|---------|---------|------|
| ... | ... | ... | ... |

## Risks and Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| [Risk 1] | [low/med/high] | [low/med/high] | [Mitigation or "accept"] |

Cover at minimum:
- Third-party service goes down or changes pricing
- Key dependency becomes unmaintained
- Hosting goes away
- Data loss
- Scope creep during agent build (yes, list this — it's the biggest one)
```

### `tech-plan.md`

```markdown
# Technical Plan — [Project Working Title]

**Version:** 1.0
**Date:** [YYYY-MM-DD]
**Status:** Ready for work breakdown
**Source:** Synthesized from `docs/02-vision/` and user preferences

---

## 1. Summary
[Two paragraphs: what is being built (one-line product description), and what stack/architecture is being used to build it.]

## 2. Stack at a Glance
[Pulled from `stack.md` — language, framework, DB, frontend, hosting in a compact table or bulleted list. Reference `stack.md` for detail.]

## 3. System Architecture Summary
[One paragraph from `architecture.md`. Reference for detail.]

## 4. Build Sequence Recommendation
A suggested order for the agents to build, so foundations exist before features depending on them. This is NOT the work breakdown (that's skill #4) — it's a phasing hint:
1. [Phase 1: e.g., "Project scaffolding, dependencies, dev environment"]
2. [Phase 2: e.g., "Database schema and migrations"]
3. [Phase 3: e.g., "Core API endpoints for primary user story"]
4. ...

## 5. Open Questions Carried Forward
[Anything from `scope.md` open questions that still hasn't been resolved, plus any new questions raised during technical planning.]

## 6. Assumptions Made During Planning
[Explicit list of every assumption made. The work breakdown skill needs to know these.]

## 7. User-Required Decisions and Actions
[Consolidated list of things the user must do or decide that an agent cannot — buying domains, creating accounts, providing API keys, etc.]

## 8. Pointers
- Stack details: `stack.md`
- Architecture: `architecture.md`
- Data model: `data-model.md`
- API contracts: `api-contracts.md`
- Auth and security: `auth-and-security.md`
- Deployment: `deployment.md`
- Dependencies and risks: `dependencies-and-risks.md`
```

## Resolving Constraint Conflicts

If two constraints from the vision artifacts contradict (e.g., "free hosting" + "GPU inference at scale," or "must be public-facing" + "must run on home network only"), stop and surface the conflict to the user with proposed resolutions:

> "Conflict: PRD says X but constraint says Y. Three ways to resolve:
> 1. [Option] — implication: ...
> 2. [Option] — implication: ...
> 3. [Option] — implication: ...
>
> Which way do you want to go?"

Wait for the user's call. Do not pick silently.

## Handoff to Next Skill

When all eight artifacts are produced and the user has signed off, end with:

> "Technical plan complete. Artifacts in `docs/03-technical/`:
> - `stack.md`
> - `architecture.md`
> - `data-model.md`
> - `api-contracts.md`
> - `auth-and-security.md`
> - `deployment.md`
> - `dependencies-and-risks.md`
> - `tech-plan.md`
>
> Next phase is breaking this into agent-ready work tickets — explicit, scoped tasks with acceptance criteria, file paths, and dependencies. That's the `agent-work-breakdown` skill. Ready when you are."

Do NOT begin the work breakdown. Stop cleanly at the planning boundary.

## What NOT to Do

- Do not write code
- Do not produce work tickets or task lists in this skill
- Do not present buffet-style menus of options — make picks
- Do not silently pick when there's a real conflict — surface it
- Do not over-engineer (no microservices, Kubernetes, or event sourcing for v1 CRUD apps)
- Do not under-justify picks — every choice needs 1–3 sentences of rationale tied to constraints
- Do not invent requirements not in the vision artifacts
- Do not skip the preferences batch — the user's preferences shape every pick

## Tone

- Direct, decisive, opinionated
- Brief rationale per pick (1–3 sentences) — the user asked for brevity
- When you're not sure, say so plainly: "Reasonable case for either X or Y here; defaulting to X because [reason]. Override if you want Y."
- Treat the vision artifacts as the source of truth; don't override them, only translate them
