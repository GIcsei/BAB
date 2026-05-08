# SYSTEM OVERVIEW

## Purpose

Multi-agent delivery system for BAB (Bank Analysis Backend) using GitHub Copilot custom agents.

## Core Principles

- `scrum-master` is the only user-facing orchestration entrypoint.
- Delegate exactly one specialist per handoff.
- Keep context small by routing to narrow ownership slices, skills, and prompts.
- Require evidence-backed deltas, explicit risks, and memory/TODO updates.
- Preserve backend behavior unless a request explicitly changes it.

## Authoritative Order

1. `agents/scrum-master.agent.md`
2. `contracts/task_contract.md`
3. `contracts/state_contract.md`
4. `contracts/memory_contract.md`
5. `contracts/delegation_contract.md`
6. `agents/AGENT_ROUTING_GUIDE.md`
7. `memory/session-state.json`
8. `memory/active-context.md`
9. `memory/TASK.md`
10. `memory/plan.md`
11. `memory/TODO.md`
12. `memory/agent-activity.md`
13. `TODO.md`

## Standard Execution Flow

1. Load live memory artifacts and routing guidance.
2. Clarify scope if the request is ambiguous.
3. Produce or confirm the minimum specialist sequence.
4. Delegate one specialist handoff.
5. Merge accepted deltas into memory and TODOs.
6. Run testing and QA gates as needed.
7. Update documentation and close.

## Backend Ownership Model

- `api-surface`: routers, schemas, endpoint contracts, OpenAPI, API docs
- `backend-implementer`: services, application orchestration, reliability refactors, behavior fixes
- `platform-infrastructure`: Firebase, Firestore, scheduler, runtime integration, Docker/TrueNAS-sensitive work
- `security-engineer`: auth, secrets, credential lifecycle, logging redaction, unsafe deserialization review
- `tester`: pytest coverage and focused verification
- `qa-engineer`: readiness review and residual risk assessment
- `documentation-writer`: verified docs, TODOs, and orchestration hygiene

## Agent Roster

- `scrum-master` (user-invocable)
- `product-owner`
- `tech-lead`
- `backend-implementer`
- `api-surface`
- `platform-infrastructure`
- `security-engineer`
- `tester`
- `qa-engineer`
- `documentation-writer`
