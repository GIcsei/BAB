# Plan: BAB Backend Multi-Agent System Refresh

Deliver a backend-specific `.github` customization layer that keeps one user-facing orchestrator, routes work to narrow specialists, reduces context with skills and prompts, and records progress durably under `.github/memory/`.

## Completed Phases

1. Analyze the BAB codebase and runtime surfaces.
2. Inspect the existing `.github` customization set and identify frontend-specific drift.
3. Review current custom-agent guidance and multi-agent orchestration practices.
4. Redesign the roster around BAB ownership boundaries.
5. Refresh prompts, skills, instructions, contracts, memory, and backlog tracking.

## Resulting Operating Model

1. `scrum-master` owns user interaction, routing, and live state.
2. `product-owner` clarifies ambiguous asks.
3. `tech-lead` determines the minimum safe specialist sequence.
4. One implementation specialist works at a time.
5. `tester` and `qa-engineer` provide focused validation and readiness review.
6. `documentation-writer` aligns docs, TODOs, and memory after verified changes.

## Validation Targets

1. Agent files contain a coherent backend roster with no frontend-project ownership drift.
2. Skills and prompts match FastAPI, services, security, scheduler, Firebase, and docs workflows.
3. Memory files reference `.github/memory/agent-activity.md` and current TODO surfaces.
4. Setup steps target Python instead of `.NET` tooling.