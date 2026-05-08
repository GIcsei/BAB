# DELEGATION CONTRACT

## Purpose

This contract defines the required response format for delegated specialist work.

`scrum-master` owns delegation, but every specialist must follow this contract when returning work.

## Required Response Shape

Every delegated response must contain exactly these five lines in this order:

1. `[START][<agent-name> | <role>] <what this agent is starting or returning>`
2. `Scope: <smallest owned slice>`
3. `Evidence: <files inspected or changed, tests run, MemoryDelta targets, or "none">`
4. `Risks: <assumptions, unknowns, or "none">`
5. `Result: <concise delta, approval, rejection, blocker, and next handoff>`

## Validation Rules

- `<agent-name>` must match exactly one agent file in `agents/`.
- `<role>` must describe the current phase contribution such as `clarification`, `architecture`, `implementation`, `testing`, `qa`, `approval`, or `documentation`.
- `Scope` must name the owned boundary and, when useful, what was deliberately not changed.
- `Evidence` must cite concrete repository evidence. Prefer file paths, tests, and MemoryDelta targets.
- MemoryDelta targets must include `memory/agent-activity.md` for meaningful delegated work.
- `Risks` must call out uncertainty instead of hiding it.
- `Result` must be actionable. If work is blocked, say what handoff is needed next.

## Rejection Rules

`scrum-master` must reject and re-request any delegated response that:

- omits one of the five required lines
- claims multiple agent identities in one banner
- reports unverified evidence
- omits memory delta intent for meaningful handoffs
- omits the delegated work summary target in `memory/agent-activity.md`
- returns broad summaries instead of a clear delta

## Handoff Discipline

- Delegate exactly one specialist per call.
- Keep each handoff scoped to one ownership area and one concrete outcome.
- Merge deltas into live state after every valid response.
