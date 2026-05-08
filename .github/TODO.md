# BAB - Multi-Agent Backlog

Updated: 2026-05-08

## Program Goal

Use one user-facing orchestrator (`scrum-master`) plus narrow backend specialists to develop, test, review, and document BAB with controlled context, explicit ownership, and durable memory.

## Active Epics

| ID | Epic | Owner | Status |
|---|---|---|---|
| E1 | API contract stability and router/schema hygiene | api-surface | Active |
| E2 | Service reliability and behavior-preserving refactors | backend-implementer | Active |
| E3 | Runtime portability across Windows, Linux, Docker, and TrueNAS | platform-infrastructure | Active |
| E4 | Auth, credential, and secret-handling hardening | security-engineer | Active |
| E5 | Pytest regression coverage and targeted verification discipline | tester | Active |
| E6 | Review readiness, memory hygiene, and docs accuracy | qa-engineer / documentation-writer | Active |

## Immediate Task Queue

| ID | Task | Delegate | Priority | Status |
|---|---|---|---|---|
| T-01 | Validate the refreshed `.github` backend orchestration with one real backend task | scrum-master | P0 | Planned |
| T-02 | Audit router response models and OpenAPI accuracy against live docs | api-surface | P1 | Planned |
| T-03 | Review service-layer duplication and narrow refactor candidates in `app/services/` | backend-implementer | P1 | Planned |
| T-04 | Re-check scheduler restore and file-lock behavior for multi-worker startup | platform-infrastructure | P1 | Planned |
| T-05 | Re-run focused auth and credential lifecycle review with current tests | security-engineer | P1 | Planned |
| T-06 | Map high-risk backend slices to focused pytest commands | tester | P2 | Planned |

## Workflow Rules

- User talks only to `scrum-master`.
- `scrum-master` delegates one specialist at a time.
- Every specialist response includes evidence, risks, and MemoryDelta targets.
- `.github/memory/agent-activity.md` records specialist summaries.
- `.github/memory/TODO.md` tracks current session execution.
- `tester` and `qa-engineer` gate risky or review-oriented closures.
- `documentation-writer` updates docs and orchestration artifacts after verified changes.
