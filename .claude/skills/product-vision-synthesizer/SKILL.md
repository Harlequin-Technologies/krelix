---
name: product-vision-synthesizer
description: Synthesize discovery interview notes into a structured set of product vision artifacts — PRD, personas, user stories, success metrics, and explicit scope. Use this skill immediately after the product-discovery-interviewer skill has produced its three discovery files, or whenever the user says "synthesize the discovery," "turn the interview into a PRD," "produce the vision docs," "build the product requirements," or "I have my discovery notes, what's next." Also trigger if the user references existing discovery notes in `docs/01-discovery/` and wants to move to formal planning. This is the second skill in a four-phase product-build pipeline; it explicitly does NOT make technical, architectural, or stack decisions — those belong to the next skill, `technical-architect-planner`. Use this skill even if the user does not name it explicitly, any time the work involves transforming raw product discovery into structured product requirements.
---

# Product Vision Synthesizer

## Purpose

This skill takes the raw outputs of the `product-discovery-interviewer` skill and produces a structured set of product vision artifacts. These artifacts answer "what are we building and why" — not "how." They are the input to the next skill (`technical-architect-planner`), which makes the technical decisions.

The user is a non-engineer building products with AI coding agents. The vision artifacts must be **explicit, unambiguous, and concrete** so that downstream skills (and ultimately the coding agents) cannot drift, invent, or expand scope.

## What This Skill Is and Is Not

**This skill IS:**
- A synthesis and structuring pass over completed discovery notes
- A gap-finder that asks targeted clarifying questions when needed
- A contradiction-surfacer that refuses to silently resolve ambiguity
- A producer of five specific artifacts in a fixed format

**This skill is NOT:**
- A second discovery interview (don't redo the interviewer's job)
- A place where new product features get invented
- Anywhere technical decisions get made (no stacks, no APIs, no data models, no UI specifics)
- A place where scope expands — if anything, scope *contracts* here as fuzzy ideas get parked or cut

## Setup (do this first)

Before any synthesis, establish:

1. **Where the discovery files live.** Default: `./docs/01-discovery/`. Confirm with the user. Read all three files (`interview-notes.md`, `parking-lot.md`, `open-questions.md`) before going further.

2. **Where the vision artifacts should be written.** Default: `./docs/02-vision/` (sibling to discovery). Confirm and create the folder.

3. **Check that discovery is sufficient.** Before synthesizing, evaluate whether the discovery notes are substantive enough to synthesize from. See the "Discovery Sufficiency Check" section below. If discovery is too thin, kick back to the user with a recommendation to return to `product-discovery-interviewer` for specific gaps.

## Discovery Sufficiency Check

The discovery notes are sufficient to synthesize from only if **all** of these are true:

- **Section 1 (Problem)** has a one-sentence problem statement AND at least one concrete real-world example
- **Section 2 (Alternatives)** lists at least 2 alternatives with reasons they fail
- **Section 3 (Solution)** has a one-paragraph description AND a one-sentence value proposition
- **Section 4 (Target User)** has a named persona (role + context), not "everyone"
- **Section 5 (Success criteria)** has at least 2 criteria, ideally measurable
- **Section 6 (Constraints)** has actual content (not all "TBD")
- **Section 7 (Non-goals)** has at least 3 explicit non-goals

If any of these fail, stop and tell the user:

> "Before I synthesize, the discovery is thin in these specific areas: [list]. I recommend going back to `product-discovery-interviewer` to fill these in. Otherwise, the synthesized artifacts will inherit those gaps and the planning phase will inherit them too. Want me to proceed anyway with explicit `[GAP — needs answer]` placeholders, or go back to discovery first?"

Let the user choose. Don't fabricate.

## Gap Analysis and Targeted Questions

Once discovery is confirmed sufficient, do a **silent gap analysis** — read all three discovery files end-to-end and identify:

1. **Ambiguities** — statements that could be interpreted multiple ways
2. **Contradictions** — places where two parts of discovery disagree (e.g., something appears in both "core to v1" and the parking lot)
3. **Missing connectives** — things that are mentioned but not linked (a user is named but their specific job-to-be-done isn't clear)
4. **Untestable success criteria** — claims that need to be made measurable

Then ask the user a **single batched message** of clarifying questions — no more than 3–5 questions total. These are surgical gap-fillers, not a new interview. Frame each question with what triggered it:

> "Before I synthesize, a few clarifying questions:
> 1. Discovery says X but the parking lot lists Y, which conflicts. Which is correct for v1?
> 2. The success criterion 'users find it useful' needs to be measurable — what observable behavior would prove that?
> 3. ..."

Wait for answers. Update interview-notes.md with answers added inline (mark them with `[Clarified during synthesis: ...]`) so the discovery record stays authoritative.

If there are zero questions, say so and proceed.

## Artifact Production Order

Produce artifacts in this order. **Present each one to the user before moving to the next.** After presenting, ask: "Any changes to this before I move on?" Make changes, then proceed.

The reason for this order: each artifact builds on the previous. The PRD is last because it pulls from all the others.

1. **`personas.md`** — Who are we building for, in detail
2. **`user-stories.md`** — What they need to do, in MoSCoW priority
3. **`scope.md`** — Explicit in-scope and out-of-scope
4. **`success-metrics.md`** — How we'll know v1 worked, measurably
5. **`prd.md`** — The consolidated requirements document

## Artifact Templates

Use these exact templates and exact section headers. Downstream skills depend on this structure.

### `personas.md`

```markdown
# Personas — [Project Working Title]

## Primary Persona: [Name or Role]

**Role / context:** [What they do, where, in what setting]

**Goals:** [What they're trying to accomplish in their day/job/life that this product touches]

**Pain points (current state):** [What's frustrating, slow, costly, or risky today — from discovery Section 1/2]

**Technical sophistication:** [Low / medium / high — comfort with the kind of tool we're building]

**How they'd find/adopt this product:** [If known from discovery; otherwise mark as open question]

## Secondary Personas (if any)

[Only include if discovery clearly named secondary users. Otherwise omit this section. Do NOT invent secondary personas.]

## Explicit Non-Users

[From discovery Section 4 "explicitly NOT for" — repeat here. These are people the product is deliberately not designed for in v1.]
```

### `user-stories.md`

```markdown
# User Stories — [Project Working Title]

Stories are written in the format: **As a [persona], I want to [action] so that [outcome].**

Each story has acceptance criteria — concrete, observable conditions that prove the story is complete.

Prioritization uses MoSCoW:
- **Must:** Required for v1. If this is missing, v1 fails.
- **Should:** Important but v1 can ship without it.
- **Could:** Nice to have if time permits.
- **Won't (this release):** Explicitly out of scope for v1.

---

## Must Have

### US-M-01: [Short title]
**As a** [persona]
**I want to** [action]
**So that** [outcome]

**Acceptance criteria:**
- [Observable condition 1]
- [Observable condition 2]
- [Observable condition 3]

---

### US-M-02: ...

## Should Have

### US-S-01: ...

## Could Have

### US-C-01: ...

## Won't Have (this release)

### US-W-01: [Short title]
[One line on why parked, references parking lot if applicable]
```

**Story discipline:**
- Each story must have at least 2 acceptance criteria
- Each "Must" story must trace back to a concrete need from discovery
- If you find yourself inventing a story not grounded in discovery, stop — it's scope creep, not synthesis
- Limit Must stories to what's truly required for the minimum viable definition from discovery Section 5

### `scope.md`

```markdown
# Scope — [Project Working Title]

## In Scope (v1)

This is what v1 explicitly includes. It maps 1:1 to the "Must Have" and "Should Have" user stories.

- [In-scope item 1] — *(US-M-01, US-M-02)*
- [In-scope item 2] — *(US-S-01)*
- [In-scope item 3] — *(US-M-03)*

## Out of Scope (v1)

This is what v1 explicitly does NOT include. This is the scope-creep firewall.

### From non-goals (discovery Section 7)
- [Non-goal 1]
- [Non-goal 2]

### From parking lot
- [Parked idea] — *[v2 / v3 / someday]*
- [Parked idea] — *[phase]*

### From "Won't Have" stories
- [US-W-01 title]

## Open Questions Still to Resolve

[Carry forward from discovery's open-questions.md, plus any new open questions surfaced during synthesis. These are flagged for the technical-architect-planner phase to address.]

- [Question 1]
- [Question 2]
```

### `success-metrics.md`

```markdown
# Success Metrics — [Project Working Title]

## Minimum Viable Definition

[From discovery Section 5 — the smallest thing that, if it worked, proves the concept. State it in one paragraph.]

## Measurable Success Criteria for v1

Each criterion must be observable and ideally measurable. "Users like it" is not a criterion; "at least 5 users return within 7 days of first use" is.

| # | Criterion | How it's measured | Target value (if applicable) |
|---|-----------|-------------------|-----------------------------|
| 1 | [Refined from discovery] | [Method] | [Value or "Yes/No"] |
| 2 | ... | ... | ... |

## Anti-Metrics

Things we explicitly do NOT want to optimize for in v1, even though we could.

- [Anti-metric 1, e.g., "raw user count" if quality matters more]
- [Anti-metric 2]
```

If discovery's success criteria can't be made measurable even after clarifying questions, list them as-is with `[needs measurable definition]` flagged. Do not invent metrics.

### `prd.md`

```markdown
# Product Requirements Document — [Project Working Title]

**Version:** 1.0 (initial vision)
**Date:** [YYYY-MM-DD]
**Status:** Draft for technical planning
**Source:** Synthesized from `docs/01-discovery/` + clarifying questions

---

## 1. Overview

[Two-paragraph summary: what is this product, who is it for, what does it do? Pulled from discovery Section 3 and refined.]

## 2. Problem Statement

[From discovery Section 1, restated cleanly. Include the concrete example and the pain.]

## 3. Goals

**Primary goal:** [What this product needs to achieve in v1]

**Supporting goals:**
- [Supporting goal 1]
- [Supporting goal 2]

## 4. Target Users

[Summary from `personas.md` — reference the file for detail.]

Primary persona: **[name/role]**

## 5. Functional Requirements

These map to user stories in `user-stories.md`. This section enumerates the capabilities the product must have, organized by area.

### 5.1 [Area, e.g., "Data ingestion"]
- [Capability 1] — *(US-M-01)*
- [Capability 2] — *(US-M-02)*

### 5.2 [Area]
- ...

## 6. Non-Functional Requirements

Things the product must be true *of*, not just things it must *do*.

- **Performance:** [If discovery surfaced any — e.g., "search results in under 5 seconds"]
- **Reliability:** [Uptime expectations, error tolerance]
- **Security / privacy:** [Sensitive data, public-records considerations, etc. — from discovery Section 6]
- **Compliance:** [Any regulated areas]
- **Accessibility:** [If mentioned]
- **Usability:** [If specific UX expectations were captured]

Mark any of these as `[Not specified in discovery]` if discovery didn't address them — do NOT invent requirements. The technical-architect-planner skill may need to surface these.

## 7. Constraints

[From discovery Section 6 — time, money, user's available hours, technical infrastructure, legal.]

## 8. Out of Scope

[Summary — reference `scope.md` for full detail.]

## 9. Success Criteria

[Summary — reference `success-metrics.md` for full detail.]

## 10. Open Questions

[Reference `scope.md` open questions section. These need answers before or during technical planning.]

## 11. Assumptions

Explicit assumptions made during synthesis that downstream phases should validate.

- [Assumption 1]
- [Assumption 2]
```

## Surfacing Contradictions

Never silently resolve a contradiction. If discovery says X but parking lot says Y, name it explicitly to the user during the clarifying-questions step. If you spot a contradiction during artifact drafting (after clarifying questions), pause and ask before proceeding.

Common contradictions to watch for:
- An idea appears in both "core solution" and the parking lot
- A success criterion contradicts a non-goal
- The target persona's described pain doesn't match the problem statement
- A constraint makes a "must" requirement impossible

## Handoff to Next Skill

When all five artifacts are produced and the user has signed off, end with:

> "Vision synthesis complete. Five artifacts are in `docs/02-vision/`:
> - `personas.md`
> - `user-stories.md`
> - `scope.md`
> - `success-metrics.md`
> - `prd.md`
>
> Next phase is technical planning — picking the stack, architecting the system, designing the data model and APIs. That's the `technical-architect-planner` skill. Ready to move on when you are."

Do NOT begin technical planning. Stop cleanly at the vision boundary.

## What NOT to Do

- Do not invent user stories, personas, or requirements not grounded in discovery
- Do not make technical decisions (no stack, no DB choice, no framework, no architecture)
- Do not propose UI designs or specific UX patterns
- Do not silently resolve contradictions
- Do not skip the discovery sufficiency check
- Do not present all artifacts at once — one at a time, with a sign-off loop on each
- Do not let new "wouldn't it be cool" ideas enter the artifacts; add them to `scope.md` open questions or `docs/01-discovery/parking-lot.md` and move on
- Do not produce artifacts if discovery is thin — kick back instead

## Tone

- Direct and structured (the user has explicitly asked for brevity)
- Surface problems plainly rather than smoothing them over
- Treat the discovery notes as the authoritative source — don't override them, only refine and structure them
- When asking clarifying questions, batch them and frame each with what triggered it, so the user understands the synthesis logic
