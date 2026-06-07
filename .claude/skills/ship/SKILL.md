---
name: ship
description: Spec-driven feature development with isolated sub-agents and Playwright verification. 5 phases - requirements, planning, task breakdown, implementation, Playwright tests. Use /ship to start or resume a feature build.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Task, AskUserQuestion, WebFetch, WebSearch
---

# Ship: Spec-Driven Feature Development

> Each feature goes through 5 phases with state persisted in `.ship/`.
> Sub-agents implement tasks in isolation. One agent writes Playwright tests. Shell verifies.

---

## STEP 0: Read State (ALWAYS DO THIS FIRST)

Read `.ship/state.json`. Based on the `phase` field, jump to the matching section below.

If the file doesn't exist:
```
Run: ./ship.sh init
```

Also read:
- `.ship/context.md` — key decisions from previous sessions
- `.ship/learnings.md` — known project issues (if it exists)

---

## Phase 1: Requirements Gathering (`phase: "requirements"`)

### Goal
Understand what feature the user wants and create `.ship/spec.md`.

### Process

1. If `.ship/spec.md` exists, read it and ask if revisions are needed
2. Otherwise ask ONE CATEGORY AT A TIME:

**Category 1: Feature Overview**
- What feature are you building?
- What problem does it solve?
- MVP scope vs nice-to-have?

**Category 2: User Stories**
- Who uses this feature?
- Walk through the user flow step by step
- Success and error cases? Edge cases?

**Category 3: Project Foundation**
- Is this a new project or a feature on an existing codebase?
- If new project: assess scope before planning
  - **Simple** (landing page, small tool, single-purpose component) → build from scratch
  - **Full SaaS / platform** (auth + payments + dashboard + database) → assess the right approach case by case
- New database tables or changes to existing ones?
- Integrations with existing services?
- New external APIs?
  - Before paying for or building custom — check free API lists first:
    - https://github.com/Free-APIs/Free-APIs.github.io
    - https://github.com/cporter202/API-mega-list

**Category 4: UI/UX**
- Where does this live in the app?
- What components are needed?
- What style/vibe? (minimal, bold, dashboard-heavy, marketing-focused, etc.)

Then run design research automatically:

1. WebSearch for 3–5 real production websites in the same niche and style

2. For each site, run both fetches in parallel:

   **A — DESIGN.md (structured design system, when available)**
   - Try `https://getdesign.md/design-md/[site-name]` via WebFetch
   - getdesign.md is a curated catalog of pre-analyzed design systems in markdown format — AI-readable design tokens, typography, color, spacing, component patterns
   - If the page exists, save to `.ship/design-refs/ref-NNN-design.md`
   - If not in the catalog, skip — don't block on it

   **B — Jina source fetch (always run this)**
   - Use WebFetch with URL: `https://r.jina.ai/https://example.com`
   - Jina returns the full page as clean markdown — layout hierarchy, nav, sections, headings, links, copy all preserved
   - Save to `.ship/design-refs/ref-NNN-source.md`

3. After all fetches, synthesize `.ship/design-notes.md`:
   - Navigation structure and layout patterns
   - Section order and page composition
   - Visual hierarchy and CTA placement
   - Component patterns (cards, hero layouts, feature grids, pricing tables, etc.)
   - Design tokens and style rules extracted from DESIGN.md files
   - Copy tone and content structure
   - Any class names or utility hints visible in the source

Goal: sub-agents get two layers — the structured design system (tokens, rules) from getdesign.md when available, plus the real page layout and content hierarchy from Jina. Together they replicate both the design logic and the layout structure, not just the aesthetic.

**Category 5: Scope Boundaries**
- What is explicitly OUT of scope?
- Known limitations for MVP?

3. Create `.ship/spec.md`:
   - Feature Summary
   - Problem Statement
   - User Stories (with acceptance criteria per story)
   - Technical Requirements
   - UI/UX Requirements
   - Integration Points
   - Out of Scope
   - Success Criteria

4. Ask user to review and approve

5. After approval:
   - Update `.ship/state.json`: set `phase` to `"planning"`
   - Log key decisions to `.ship/context.md`

---

## Phase 2: Technical Planning (`phase: "planning"`)

### Goal
Design how the feature integrates with the existing architecture. Create `.ship/plan.md`.

### Process

1. Read:
   - `.ship/spec.md`
   - `.ship/context.md`
   - `.ship/learnings.md` (apply relevant lessons if it exists)
   - `CLAUDE.md` or `.claude/CLAUDE.md`
   - Existing files related to the feature area

2. Create `.ship/plan.md` covering:

**Section 1: Architecture Integration**
- How this fits the existing project structure
- Existing patterns to follow
- New routes, endpoints, or components needed

**Section 2: Database Changes**
- New tables/columns with schema
- Migrations needed

**Section 3: API Design**
- New routes (method, path, request/response)
- Auth requirements

**Section 4: Frontend Components**
- New pages and routes
- Components to create
- State management approach
- Read `.ship/design-notes.md` and `.ship/design-refs/` — reference the extracted layout patterns when defining component structure. Sub-agents must use these files, not generic assumptions about layout.

**Section 5: Service Integration**
- External services needed

**Section 6: File Map**
- Complete list of files to create or modify

3. Present plan and ask for approval

4. After approval:
   - Update `.ship/state.json`: set `phase` to `"breakdown"`
   - Log technical decisions to `.ship/context.md`

---

## Phase 3: Task Breakdown (`phase: "breakdown"`)

### Goal
Break the plan into small sequential tasks for sub-agent execution.

### Process

1. Read `.ship/spec.md` and `.ship/plan.md`

2. Break into tasks:

**Sizing:** 15-45 min each, 1-5 files, one clear purpose

**Ordering:**
1. Database schema/migrations
2. Backend API routes
3. Frontend components and pages
4. Wiring (frontend ↔ backend)
5. Service integrations
6. Polish and edge cases

3. For EACH task create `.ship/tasks/task-NNN.md`:

```markdown
# Task NNN: [Title]

## Type
ui  ← only include this line for tasks involving UI/UX (components, pages, forms, layouts, styling)
    ← omit entirely for backend, API, DB, or config tasks

## Description
[What to implement and why]

## Files
- `path/to/file.ts` (create|modify)

## Requirements
1. [Specific requirement]

## Existing Code to Reference
- `path/to/existing.ts` (pattern to follow)

## Acceptance Criteria
- [ ] [Criterion]

## Dependencies
- Task NNN (if any)

## Commit Message
type: description
```

4. Create `.ship/tasks.md` (master checklist):
```markdown
# Feature Tasks: [Feature Name]
Generated: [timestamp]
Total: [N] tasks

## Checklist
- [ ] 001: [Title]
- [ ] 002: [Title]
```

5. Update `.ship/state.json`:
   - `phase` → `"implementation"`
   - `total_tasks` → count
   - `current_task` → 1

6. Tell the user:
   > Tasks are ready. Run `./ship.sh run all` for automated execution.

---

## Phase 4: Implementation (`phase: "implementation"`)

Sub-agent execution is handled by `ship.sh`:

```bash
./ship.sh run          # Run next task
./ship.sh run 5        # Run specific task
./ship.sh run all      # Run all remaining tasks
./ship.sh status       # Check progress
./ship.sh skip 5       # Skip a task
```

### If user wants to run tasks in THIS session:

Use the Task tool for partial isolation:
```
Task tool → subagent_type: "general-purpose"
prompt: "Read .ship/tasks/task-005.md, .ship/spec.md, .ship/plan.md, .ship/context.md.
Implement ONLY task 5. Commit with the exact message specified. Do not read other task files.
If you discover something non-obvious, append a brief note to .ship/learnings.md."
```

---

## Phase 5: Testing (`phase: "testing"`)

### Goal
One agent reads the spec and writes Playwright tests covering the acceptance criteria. Then shell verifies.

```bash
./ship.sh tests    # One agent writes Playwright tests from spec
./ship.sh verify   # Shell runs Playwright — no agent, pass/fail only
```

### The test-writing agent:
1. Reads `spec.md` — acceptance criteria drive the tests
2. Reads `plan.md` — understands what was built
3. Reads the implemented files
4. Writes Playwright tests covering real user flows end-to-end
5. Runs `npx playwright test` to confirm discovery

### Handling failures
- If `./ship.sh verify` fails: check `.ship/logs/verify.log`
- Fix the failing test or the implementation, then run `./ship.sh verify` again
- When all tests pass: `phase` → `complete`, `verified` → `true`

---

## Context Recovery

Every time `/ship` is invoked:

1. Read `.ship/state.json` → current phase
2. Read `.ship/context.md` → key decisions
3. Read `.ship/learnings.md` → known issues (if exists)
4. Based on phase:
   - `requirements` → Read `.ship/spec.md` if it exists
   - `planning` → Read `.ship/spec.md` + `.ship/design-notes.md` (if exists)
   - `breakdown` → Read `.ship/spec.md` + `.ship/plan.md` + `.ship/design-notes.md` (if exists)
   - `implementation` → Read `.ship/tasks.md` + current task file + `.ship/design-refs/` (for UI tasks)
   - `testing` → Read `.ship/spec.md` + `.ship/plan.md`

---

## State File Format

```json
{
  "project": "ship",
  "feature": "feature-name",
  "phase": "requirements|planning|breakdown|implementation|testing|verifying|complete",
  "current_task": 0,
  "total_tasks": 0,
  "completed_tasks": [],
  "skipped_tasks": [],
  "failed_tasks": [],
  "playwright_cmd": "npx playwright test",
  "tests_written": false,
  "verified": false,
  "created_at": "ISO-timestamp",
  "updated_at": "ISO-timestamp"
}
```

## Directory Structure

```
.ship/
  state.json          # Phase tracking and progress
  context.md          # Key decisions log (persists across sessions)
  learnings.md        # Non-obvious discoveries (persists across features)
  spec.md             # Feature specification (Phase 1 output)
  design-notes.md     # Extracted layout patterns from reference sites (Phase 1 output)
  design-refs/        # Per-site: ref-NNN-source.md (Jina) + ref-NNN-design.md (getdesign.md, if available)
  plan.md             # Technical plan (Phase 2 output)
  tasks.md            # Master task checklist (Phase 3 output)
  tasks/              # Individual task files for sub-agents
  logs/               # Sub-agent execution logs + verify.log
  blockers/           # Blocker reports from sub-agents
  .gitignore          # Excludes logs and blockers
```
