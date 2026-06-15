# Owner Task Planning Design

This document defines the v1 contract for turning a user request into Project,
Epic, Sub Epic, Task, and Memory records.

The Owner is allowed to think deeply. Workers are expected to execute small,
clear tasks.

## Role Boundary

- Owner owns project design, task decomposition, prioritization, task creation,
  worker assignment, review, and merge judgment.
- API Worker is a helper for summaries, log analysis, draft notes, and research.
- API Worker must not directly create authoritative tasks or command Code
  Workers without Owner review.
- Workspace/Code Workers execute tasks from the server queue.
- Test Runner validates builds, runtime behavior, screenshots/videos/logs, and
  artifacts.

## Goals

- Convert one user objective into a project tree that workers can execute.
- Keep worker tasks near 15 minutes of focused work.
- Store durable decisions as memory.
- Avoid asking the user unless the decision changes product direction, cost,
  credentials, external services, or engine/tooling lock-in.
- Produce tasks that can be leased by the existing worker APIs without special
  interpretation.
- Keep task creation authority with Owner, not with helper workers.

## Non Goals

- Do not build a full product management system in v1.
- Do not require a game engine choice before the first project is planned.
- Do not let the Owner directly implement game code except for small control
  plane fixes.
- Do not store raw chat logs as memory.
- Do not let API Worker become a hidden planner or manager.
- Do not let Worker-to-Worker discussion bypass Owner task creation.

## Planning Inputs

The Owner planning step should receive:

- User objective.
- Optional user constraints.
- Existing project tree, if any.
- Owner dashboard summary.
- Pending/running/failed task queue summary.
- Relevant memories:
  - `design`
  - `project_rules`
  - `coding_rules`
  - `project_knowledge`
  - `art_guide`
  - `narrative_guide`
- recent `task_history`
- Model profile summary, only as capability context.
- Project `owner-design` thread summary.
- Project `owner-tasks` thread summary.
- Relevant AI-internal task summaries, only when needed.

## Planning Output

The Owner must return a structured plan with these sections:

1. Decision summary.
2. User questions, only if blocked.
3. Memory writes.
4. Project changes.
5. Epics.
6. Sub Epics.
7. Tasks.
8. Review notes.

If no user decision is required, `User questions` must explicitly say `none`.

Owner should discuss design with the user in the project `owner-design` thread.
Owner should split approved design into tasks in the project `owner-tasks`
thread. Workers do not participate in these Owner/user threads.

Owner should not force a single intent label on user messages. A user message
may contain multiple requests. Owner should infer the meaning, split it into one
or more proposed actions, ask about risky or ambiguous actions, and store
actions/tags/summaries for retrieval.

## Project Tree Rules

Project:

- One project maps to one game repository.
- Engine may be `undecided`, `unity`, `unreal`, `godot`, `custom`, or a short
  lowercase engine tag.
- Repository and workspace config may be empty during design, but workspace
  workers will skip tasks until project config exists.

Epic:

- Represents a meaningful slice of game development, such as bootstrap,
  prototype combat, test harness, art pipeline, or build automation.
- Should be stable for days or weeks.

Sub Epic:

- Represents a worker-sized area of sequencing, such as input foundation,
  player controller, enemy prototype, CI build smoke test, or template docs.
- Should contain tasks that can be reviewed together.

Task:

- Represents one worker execution.
- Must have one role.
- Must have concrete success criteria.
- Must have a `worker/` branch.
- Should be estimated at 15 minutes by default.
- May be 30 minutes only when splitting would make the result less testable.
- Must not exceed 60 minutes in v1 without explicit Owner justification.

## Task Sizing

The default target is 15 minutes.

Use 15 minutes for:

- Create or edit one small file.
- Add one narrow test.
- Wire one endpoint or schema field.
- Add one script flag.
- Fix one known error from logs.
- Write one focused design document section.

Use 30 minutes for:

- A change that touches two closely related files.
- A build/test command integration where the validation loop is part of the
  work.
- A small template scaffold with docs and smoke check.

Split the task when:

- It spans unrelated systems.
- It needs product judgment and implementation.
- It changes server API and worker behavior at the same time.
- It requires more than one validation mode.
- The success criteria contain the word `and` more than twice.

## Branch Naming

Every workspace task branch must start with `worker/`.

Recommended pattern:

```text
worker/{task-area}-{short-goal}
```

Examples:

```text
worker/template-readme
worker/test-runner-contract-doc
worker/player-input-stub
worker/fix-health-check
```

Branch names should be lowercase, short, and stable after task creation.

## Memory Write Rules

Create memory when the information should survive beyond the current run.

Use `design` for:

- Architecture decisions.
- Game design constraints.
- Engine-independent template decisions.

Use `project_rules` for:

- Repository layout rules.
- Branch and merge policy.
- Test evidence rules.

Use `coding_rules` for:

- Engine-specific coding conventions.
- Formatting and dependency constraints.

Use `project_knowledge` for:

- Existing file layout.
- Implemented systems.
- Known quirks.

Use guide memories for creative continuity:

- `art_guide`
- `narrative_guide`

Use `task_history` only for worker reports. The server already writes these.

Memory keys should be stable and namespaced:

```text
project:{project_slug}:design:{topic}
project:{project_slug}:rules:{topic}
template:{template_slug}:design:{topic}
```

## User Decision Gates

Stop and ask the user when the plan requires:

- Selecting the first real game engine.
- Spending money or increasing model cost materially.
- Adding external paid services.
- Storing or changing credentials.
- Deleting project history or force-pushing.
- Changing merge warnings from advisory to blocking.
- Choosing between materially different game concepts.
- Accepting legal/licensing risk.

Decision gates are judgment-based, not list-only. The examples above are not
exhaustive. Owner should stop when an action is risky, costly,
security-sensitive, public, destructive, hard to reverse, direction-changing, or
ambiguous.

Do not stop for:

- File naming.
- Task splitting.
- Conservative placeholder engine value.
- Adding docs or local tests.
- Choosing default branch name format.

## Owner Planning Prompt Shape

The Owner command prompt should include:

```text
You are the Owner for AI Game Company v1.

Plan only. Do not implement worker code unless the task is a small server
control-plane fix.

Return:
- decision_summary
- user_questions
- memory_writes
- project_changes
- epics
- sub_epics
- tasks
- review_notes

Task constraints:
- default estimated_minutes is 15
- branch must start with worker/
- requirements and success_criteria must be concrete
- store durable decisions as memory
- ask the user only for decision gates
```

## Minimal Task JSON

The Owner may create tasks through the existing API with:

```json
{
  "role": "code_worker",
  "goal": "Add a smoke test command to the project template docs",
  "requirements": [
    "Document the command that verifies the template without engine tooling",
    "Keep the command engine-agnostic"
  ],
  "success_criteria": [
    "The documented command can run on a fresh template checkout",
    "The task report includes the command output"
  ],
  "estimated_minutes": 15,
  "memory_refs": [
    "template:engine_agnostic:design:layout"
  ],
  "branch": "worker/template-smoke-command"
}
```

## Readiness Checks Before Enqueue

Before creating workspace tasks, Owner should verify:

- Project has `repo_url`.
- Project has `workspace_path`.
- Base branch is known or defaults to `main`.
- Task branch starts with `worker/`.
- Task success criteria mention test/build/manual evidence.

If the project is not workspace-ready, Owner may still create design tasks, but
should not create executable workspace tasks unless the missing config is the
task itself.

## v1 Implementation Plan

1. Keep this document as the planning contract.
2. Update `build_owner_prompt` to reference this output shape.
3. Add optional local helper that validates Owner task JSON before creation.
4. Add API tests for invalid long tasks only if the server starts enforcing a
   stricter maximum than the current schema.
5. Later, add `/owner/plans` if raw Owner planning outputs need durable storage.
