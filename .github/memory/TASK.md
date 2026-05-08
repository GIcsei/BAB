# ACTIVE TASK

- Task ID: BAB-GITHUB-AGENT-REFRESH-2026-05-08
- Request: Clean up and refactor `.github` agents, prompts, skills, instructions, contracts, memory, and TODO tracking for BAB backend development.
- Owner: scrum-master
- Stage: done
- Priority: high
- Started: 2026-05-08
- Finished: 2026-05-08

## Acceptance Criteria

- [x] Remove stale frontend-specific agent files and prompts that do not fit BAB.
- [x] Keep one user-facing orchestrator with delegated backend specialists.
- [x] Rewrite specialists around current BAB ownership boundaries.
- [x] Use skills, prompts, instructions, and contracts to narrow specialist context.
- [x] Require memory summaries under `.github/memory/` for delegated work.
- [x] Refresh `.github/TODO.md` and `.github/memory/TODO.md` as durable task trackers.

## Evidence

- Backend-focused agent roster defined in `.github/agents/`.
- Routing and system docs updated for BAB architecture.
- Memory surfaces reset around backend orchestration and agent activity logging.
- Stale frontend-specific backlog and orchestration language removed.
