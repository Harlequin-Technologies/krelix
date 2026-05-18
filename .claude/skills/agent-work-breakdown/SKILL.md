---
name: agent-work-breakdown
description: Convert a completed technical plan into a set of agent-ready work tickets — small, sequenced, unambiguous tasks with file paths, acceptance criteria, and explicit out-of-scope guards that a coding agent (Claude Code, Cursor, etc.) can execute one at a time without drifting. Use this skill immediately after `technical-architect-planner` has produced the artifacts in `docs/03-technical/`, or whenever the user says "break this into tickets," "produce the work breakdown," "create tasks for the agents," "I have the tech plan, what do I tell Claude Code," or "turn the plan into work items." Also trigger when the user has a tech plan in hand and wants to start building with AI coding agents. This is the fourth and final skill in the product-build pipeline — it produces the artifacts that drive actual coding work. Use this skill any time the work involves converting technical decisions into explicit agent instructions.
---

# Agent Work Breakdown

## Purpose

This skill produces the artifacts that drive actual coding work. The user is a non-engineer who will hand each ticket to a coding agent (Claude Code, Cursor, or similar). The tickets must be:

- **Unambiguous** — agents can't drift if there's nothing to drift toward
- **Small** — sized to one agent session (~1–4 hours of work)
- **Bounded** — explicit out-of-scope for each ticket, plus "don't touch" file lists
- **Traceable** — every ticket maps back to a user story or technical decision
- **Sequenced** — dependencies are explicit so phases build correctly

The user has been burned by scope creep twice. The ticket structure is the final firewall.

## What This Skill Is and Is Not

**This skill IS:**
- A converter from technical plan to executable work units
- A producer of project-wide agent guidance (style, commit format, decision-making rules)
- The handoff to actual coding work

**This skill is NOT:**
- A place to make new technical decisions (those are locked in `docs/03-technical/`)
- A place to write code
- A place to second-guess the plan (if the plan is wrong, kick back to skill #3)

## Setup (do this first)

1. **Technical artifact location.** Default: `./docs/03-technical/`. Read all eight files. The master is `tech-plan.md` — its Section 4 "Build Sequence Recommendation" is the phase backbone.

2. **Also re-read these from vision:** `docs/02-vision/user-stories.md` and `docs/02-vision/scope.md`. Every ticket must trace back to a Must/Should story.

3. **Ticket destination.** Default: `./docs/04-tickets/`. Confirm and create.

4. **Tech plan sufficiency check.** Verify the technical artifacts are substantive (stack picked, data model concrete, API contracts have endpoints with shapes, deployment target named). If not, kick back to `technical-architect-planner` with specifics.

## Ticket Sizing Discipline

Each ticket should be **one agent session** of work — roughly 1–4 hours of focused agent time.

**Signs a ticket is too big — split it:**
- Touches more than ~5 files
- Mixes infrastructure setup with feature work
- Has more than 6 acceptance criteria
- Description has the word "and" connecting two distinct outcomes
- Spans multiple architectural components

**Signs a ticket is too small — consolidate it:**
- Less than 30 minutes of work
- Only one trivial file change with no testable outcome
- Can't articulate a meaningful acceptance criterion

When in doubt, split. Smaller tickets fail more visibly and recover faster.

## Phase-by-Phase Workflow

Generate tickets **one phase at a time**, using the phases from `tech-plan.md` Section 4 as the backbone. After generating each phase, present the tickets to the user for sign-off before generating the next phase.

For each phase:
1. Recap the phase goal in one sentence
2. List the tickets that belong to it (T-numbers and titles)
3. Show the dependency graph for the phase (which tickets block which)
4. Present each ticket fully
5. Ask: "Any changes to this phase before I move to [next phase]?"

This phased presentation prevents the user from being buried in 40 tickets at once and lets corrections cascade properly.

## Numbering and Naming

- **T-numbers are sequential and permanent.** T001, T002, T003, etc. Even if a ticket is later cut, its number is not reused.
- **Filename format:** `T001-short-kebab-title.md` (e.g., `T001-project-scaffolding.md`).
- Phases don't get their own number prefix — phase membership lives inside the ticket and in the index.

## Output Artifacts

All in `docs/04-tickets/`:

1. **`000-index.md`** — master list, dependency graph, copy-paste prompt template, completion checklist
2. **`agent-guidance.md`** — project-wide rules every ticket inherits
3. **`definition-of-done.md`** — what "done" means everywhere
4. **`user-actions.md`** — things only the user can do
5. **`T001-*.md`, `T002-*.md`, ...** — individual tickets

Produce files 2, 3, and 4 first (they're project-wide). Then generate tickets phase by phase.

## Artifact Templates

### `agent-guidance.md`

```markdown
# Agent Guidance — [Project Working Title]

Project-wide rules that every ticket inherits. Read this before working any ticket.

## Project Context
[Two paragraphs: what this product is, who it's for, what stack it uses. Pulled from PRD and stack.md.]

## How to Approach a Ticket
1. Read this file
2. Read the ticket
3. Read `definition-of-done.md`
4. Read any file the ticket lists under "Read for context" or "Files to modify"
5. Plan before coding — surface the plan if anything is unclear
6. Implement only what the ticket asks for
7. Stop at the ticket's acceptance criteria

## When to Decide vs. Ask
**Decide on your own:**
- Function and variable naming
- Internal class/module structure not specified
- Standard library vs. small utility helpers
- Code style within the project's style rules
- Test names and structure

**Ask the user before proceeding:**
- Adding any new third-party dependency (even small ones)
- Changing the data model shape
- Changing API contract shapes
- Anything in the ticket's "Out of scope" or "Don't touch" lists
- Anything that contradicts the technical plan

## Refactoring Policy
Do not refactor code outside the ticket's "Files to modify" list. If you notice something worth refactoring elsewhere, leave a `# TODO(refactor): [note]` comment and mention it in the ticket completion summary — do not fix it in this ticket.

## Style Rules
[Pulled from stack.md if specified. Otherwise sensible defaults:]
- Follow standard formatting for the chosen language (e.g., `black` for Python, `prettier` for JS)
- Linting: [tool from stack.md, or "use the language's standard"]
- Naming: [snake_case Python, camelCase JS, etc. — match the language]
- Comments: explain *why*, not *what*

## Commit Message Format
Use Conventional Commits:
- `feat(scope): summary` — new feature
- `fix(scope): summary` — bug fix
- `refactor(scope): summary` — internal change, no behavior diff
- `docs(scope): summary` — documentation
- `test(scope): summary` — tests only
- `chore(scope): summary` — build, deps, config

Scope is the area of code or the ticket number, e.g., `feat(T012): add salary search endpoint`.

## When You Get Stuck
- If the ticket is ambiguous, ask the user before guessing
- If the technical plan contradicts itself, surface the conflict — don't pick silently
- If acceptance criteria can't all be satisfied as written, say so

## What Never to Do
- Never expand scope mid-ticket — if it doesn't serve the acceptance criteria, it doesn't belong
- Never touch files outside "Files to modify" without permission
- Never add features that weren't requested
- Never silently swap out libraries or frameworks chosen in the tech plan
```

### `definition-of-done.md`

```markdown
# Definition of Done — [Project Working Title]

A ticket is "done" only when ALL of these are true:

1. **All acceptance criteria from the ticket are met and observable**
2. **Code compiles / runs without errors**
3. **[Tests pass / no tests required — pick one based on stack.md]**
4. **Linting passes** ([tool from agent-guidance.md])
5. **No `TODO(this-ticket)` markers remain** — TODOs for *other* tickets are fine and should be left
6. **Commit messages follow the format in `agent-guidance.md`**
7. **The ticket's status block is updated** (see ticket template — "Status" goes to "Done" with a one-line completion summary)
8. **Any deviations from the ticket are called out in the completion summary**
9. **Files listed under "Files to NOT touch" were not modified**

If any item is false, the ticket is not done. Do not mark done prematurely.
```

### `user-actions.md`

```markdown
# User-Required Actions — [Project Working Title]

These items must be performed by the user, not the agents. They typically involve authentication, money, identity, or external accounts. Each item lists what's needed, when in the build sequence it's needed, and how to provide it to the agents (e.g., where to paste an API key, what to name a `.env` variable).

## Before Build Starts
- [ ] [Action 1, e.g., "Register domain name `example.com`"]
- [ ] [Action 2, e.g., "Create GitHub repo"]

## Before Phase X
- [ ] [Action, e.g., "Sign up for Stripe account, paste live key into `.env` as STRIPE_API_KEY"]

## Before Deployment
- [ ] [Action, e.g., "Point DNS records to host IP"]
```

Pull these from `deployment.md` "User-Required Actions" and from `tech-plan.md` Section 7. Do not invent new user actions — only consolidate existing ones.

### Individual Ticket Template

Filename: `TNNN-short-kebab-title.md`

```markdown
# T001 — [Short title]

**Status:** Not started
**Phase:** [Phase number and name from tech-plan.md]
**Estimated session length:** [30 min / 1 hr / 2 hr / 3 hr / 4 hr]
**Depends on:** [List of T-numbers that must be done first, or "None"]
**Blocks:** [List of T-numbers that can't start until this is done, or "None"]
**Maps to:** [User story IDs (US-M-01, etc.) and/or tech-plan sections this implements]

---

## Objective
[One sentence: what gets built or changed in this ticket.]

## Context
[2–4 sentences of background the agent needs. Why this ticket exists, where it sits in the system, anything non-obvious. Reference the technical artifacts the agent should read for deeper context — e.g., "See `docs/03-technical/data-model.md` for the Employee entity."]

## Read for context
- `docs/03-technical/[relevant file].md`
- [Any other files the agent needs to read before starting]

## Files to create
- `path/to/file.py` — [one-line purpose]
- `path/to/other.html` — [one-line purpose]

## Files to modify
- `path/to/existing.py` — [what changes, in one line]

## Files to NOT touch
[Files in or near the work that the agent should NOT modify. This is the per-ticket scope-creep firewall. Examples: "Database migration files older than this ticket's", "The HTML template — that's a separate ticket", etc.]
- `path/to/leave-alone.py`

## Steps
[Numbered, concrete steps. Each step is something the agent does. Not pseudocode — just the work breakdown.]
1. [Step 1]
2. [Step 2]
3. [Step 3]

## Acceptance Criteria
[Observable, testable conditions. Each item must be checkable by running the code or reading a file, not by interpretation.]
- [ ] [Criterion 1, e.g., "GET /api/v1/employees returns 200 with JSON array shape from api-contracts.md"]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

## Out of Scope (for this ticket)
[Things that might seem related but belong elsewhere. Explicit list. Examples:]
- Authentication (T015 handles this)
- Pagination (T009)
- Search filters beyond the `q` parameter (T010)

## Notes
[Anything else the agent needs to know — gotchas, things tried before, external doc links if highly relevant.]

---

## Completion Summary
[The agent fills this in when the ticket is done.]
- **Files touched:**
- **Deviations from the ticket (if any):**
- **TODOs left for other tickets:**
- **Commit hashes:**
```

### `000-index.md`

```markdown
# Ticket Index — [Project Working Title]

Master list of all work tickets, dependency graph, and the prompt template for handing tickets to a coding agent.

## How to Work a Ticket
1. Open the ticket file (`TNNN-*.md`)
2. Use the **Agent Prompt Template** below — replace `[TICKET NUMBER]` with the ticket
3. Paste into Claude Code / Cursor / your coding agent of choice
4. When the agent reports done, verify each acceptance criterion yourself before checking the box below

## Agent Prompt Template
Copy this exactly when starting a ticket:

> Working ticket [TICKET NUMBER] for [project name].
>
> Before starting:
> 1. Read `docs/04-tickets/agent-guidance.md`
> 2. Read `docs/04-tickets/definition-of-done.md`
> 3. Read `docs/04-tickets/[TICKET NUMBER]-*.md`
> 4. Read every file the ticket lists under "Read for context"
>
> Then plan the work and surface the plan before coding. Do not start coding until I confirm the plan. When you finish, update the ticket's Completion Summary and report which acceptance criteria pass.

## Phase Map

### Phase 1 — [Name]
[One sentence on what this phase accomplishes.]

| # | Title | Depends on | Status |
|---|-------|------------|--------|
| T001 | [Title] | — | ☐ Not started |
| T002 | [Title] | T001 | ☐ Not started |

### Phase 2 — [Name]
...

## Dependency Graph
[Text-based dependency listing. For each ticket, show what blocks it. Optional ASCII or Mermaid if useful.]

```
T001 → T002 → T003
            ↘ T004
T005 (independent)
```

## Completion Checklist
[Master checkboxes — one per ticket. Mirror the phase-map status.]
- [ ] T001 — [Title]
- [ ] T002 — [Title]
- [ ] T003 — [Title]
- ...

## User-Required Actions
See `user-actions.md` for things the user must do alongside the agent work.
```

## Traceability Requirement

Every ticket must have a non-empty `Maps to:` field. If you find yourself drafting a ticket that doesn't map to any user story or technical decision, **the ticket is invalid** — either it's scope creep or the vision/plan is missing something. Surface the gap to the user instead of writing the ticket.

Acceptable mappings:
- A user story ID (e.g., `US-M-03`)
- A specific technical decision (e.g., `stack.md - Database`, `architecture.md - Frontend component`)
- A non-functional requirement from `prd.md` (e.g., `PRD Section 6 - Performance: search under 5 seconds`)
- A risk mitigation from `dependencies-and-risks.md`

Foundational tickets (e.g., "project scaffolding," "set up CI") map to the build sequence in `tech-plan.md` Section 4. That's fine.

## Common Phase Patterns

While phases come from `tech-plan.md`, here are typical patterns you'll see and how to break them down:

- **Scaffolding phase:** repo structure, dependency manifest, dev environment, `.env.example`, README. Usually 2–4 tickets.
- **Data layer phase:** schema migrations, models/ORM, seed data, any reference data import. One ticket per entity is often right.
- **API phase:** one ticket per endpoint group (often one ticket per user story's set of endpoints).
- **Frontend phase:** one ticket per view/page, or per component group.
- **Auth phase:** even for "no auth," there's usually a ticket for input validation and rate limiting.
- **Deployment phase:** Dockerfile/Caddyfile/systemd unit, CI/CD pipeline, DNS, TLS, smoke test.
- **Polish phase:** error pages, logging, monitoring, README, deploy docs.

These are starting templates. The actual tickets come from the actual technical plan — don't force-fit.

## Surfacing Problems

If during ticket generation you realize:
- The technical plan is missing something needed
- Two technical artifacts contradict each other
- A user story can't be implemented with the chosen stack
- Acceptance criteria from a user story aren't translatable to code

**Stop and surface it.** Do not invent your way around the gap. Ask the user how to proceed — fix the upstream artifact, or accept a documented assumption.

## Handoff to Implementation

When all tickets are produced and the user has signed off, end with:

> "Work breakdown complete. Artifacts in `docs/04-tickets/`:
> - `000-index.md` — master list with prompt template
> - `agent-guidance.md` — project-wide agent rules
> - `definition-of-done.md` — what 'done' means
> - `user-actions.md` — things only you can do
> - [N] individual tickets (T001 through T0NN)
>
> To start building, open `000-index.md`, copy the Agent Prompt Template, fill in T001, and paste it into Claude Code. Verify acceptance criteria yourself before checking off each ticket.
>
> If you hit a problem mid-build that requires re-planning, come back here — but try to resist scope expansion at the ticket level. If something genuinely needs to change, route it through the right phase: vision change → skill #2, technical change → skill #3."

## What NOT to Do

- Do not invent tickets not grounded in earlier artifacts
- Do not make new technical decisions — kick back to skill #3 if needed
- Do not present all tickets at once — phase by phase, sign-off between phases
- Do not write tickets that span multiple architectural components
- Do not omit "Files to NOT touch" — it's the per-ticket firewall
- Do not omit "Out of scope for this ticket" — same reason
- Do not skip the prompt template in `000-index.md` — that's how the user actually uses these
- Do not write code in tickets — tickets describe work, agents do work

## Tone

- Direct and structured
- Each ticket should read like a work order, not an essay
- When something is missing or unclear, name it plainly and stop
