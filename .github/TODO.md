# BAB - Multi-Agent Backlog

Updated: 2026-05-10

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
| E7 | Release Stability Sprint — 4-phase consolidation and hardening | multi-specialist | Active |

## Immediate Task Queue

| ID | Task | Delegate | Priority | Status |
|---|---|---|---|---|
| T-01 | Validate the refreshed `.github` backend orchestration with one real backend task | scrum-master | P0 | Completed |
| T-02 | Audit router response models and OpenAPI accuracy against live docs | api-surface | P1 | Completed |
| T-03 | Review service-layer duplication and narrow refactor candidates in `app/services/` | backend-implementer | P1 | Completed |
| T-04 | Re-check scheduler restore and file-lock behavior for multi-worker startup | platform-infrastructure | P1 | Completed |
| T-05 | Re-run focused auth and credential lifecycle review with current tests | security-engineer | P1 | Completed |
| T-06 | Map high-risk backend slices to focused pytest commands | tester | P2 | Completed |

## Release Stability Sprint Tasks (E7)

Link to detailed plan: [`.github/memory/RELEASE_PLAN.md`](.github/memory/RELEASE_PLAN.md)

| ID | Task | Delegate | Priority | Status |
|---|---|---|---|---|
| T-07 | Phase 1: Consolidate Firestore services — eliminate duplication | backend-implementer | P0 | Completed |
| T-08 | Phase 2: Improve logging, auth token refresh, scheduler reliability | backend-implementer | P0 | Completed |
| T-09 | Phase 3: Secure parquet streaming and file access controls | api-surface | P0 | in-progress |
| T-10 | Phase 4: Fix Docker release builds and CI/CD workflow | platform-infrastructure | P0 | not-started |
| T-11 | CI gate recovery: fix pytest, bandit, and mypy blockers from full verification run | backend-implementer | P0 | completed |
| T-12 | Add BAB version readout to `/health` with validation and docs sync | api-surface | P1 | completed |

## Workflow Rules

- User talks only to `scrum-master`.
- `scrum-master` delegates one specialist at a time.
- Every specialist response includes evidence, risks, and MemoryDelta targets.
- `.github/memory/agent-activity.md` records specialist summaries.
- `.github/memory/TODO.md` tracks current session execution.
- `tester` and `qa-engineer` gate risky or review-oriented closures.
- `documentation-writer` updates docs and orchestration artifacts after verified changes.
