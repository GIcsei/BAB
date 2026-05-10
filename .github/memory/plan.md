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

## Active Execution Sequence (2026-05-08)

1. Tech-lead defines smallest safe dependency order for implementing all currently open points.
2. Platform-infrastructure executes the first runtime/deploy blocker bundle.
3. Security-engineer executes auth/secret/input hardening bundle and dependency vulnerability checks.
4. Backend-implementer and api-surface execute behavior-preserving reliability and contract-safe fixes.
5. Tester runs focused pytest validation for every changed surface.
6. QA-engineer performs readiness review on residual risk.
7. Documentation-writer synchronizes docs/TODO/memory after verified behavior.

## Stable Release Execution (2026-05-10)

Tech-lead sequenced 7 open issues into 4 distinct phases:

- **Phase 1** (`feature/consolidate-firestore-services`): Backend-implementer eliminates Firestore service duplication (#3).
- **Phase 2** (`feature/improve-logging-auth-scheduler`): Backend-implementer hardens logging, token refresh, and scheduler (#2, #1, #7).
- **Phase 3** (`feature/secure-parquet-streaming`): API-surface secures file access and streaming (#5, #6).
- **Phase 4** (`infra/fix-release-docker`): Platform-infrastructure fixes Docker and CI/CD (#4).

Execution: Phase 1 unblocks Phases 2+3 (parallel). Phase 4 runs independently.

See [`.github/memory/RELEASE_PLAN.md`](.github/memory/RELEASE_PLAN.md) for full details.

## Release Sprint Progress (2026-05-10)

1. Completed: Phase 1 (T-07 / issue #3) by consolidating Firestore user block/unblock writes into a single Firestore service method and updating login/registration callers.
2. Validation: focused unit test command passed with 42 passed and 0 failed.
3. Tester gate: focused Phase 1 regression tests passed with 25 passed and 0 failed.
4. QA gate: conditional pass for Phase 1 with residual recommendation to verify field-preservation semantics on populated `users/{user_id}` documents.
5. Completed: Phase 2 (T-08 / issues #2, #1, #7) by improving startup logging consistency, adding expiration-aware token normalization and safer refresh fallback handling, and reducing scheduler startup restore race via leadership bootstrap.
6. Validation: focused Phase 2 command passed with 27 passed and 0 failed; adjacent compatibility command passed with 17 passed and 0 failed (1 warning).
7. Completed: second-run hardening for Phase 2 residual risks (legacy relative-expiry ambiguity and non-`fcntl` leader behavior) with focused follow-up tests passing (16 passed).
8. Peer-review gates: tester revalidation passed (focused 16 + broader targeted 78, 0 failed); security follow-up conditional pass; QA final conditional pass with release guardrails for non-`fcntl` override governance.
9. Next: Phase 3 (`api-surface`) and Phase 4 (`platform-infrastructure`) remain queued.
10. Post-phase hotfix: added scheduler per-user in-flight dedupe to prevent overlapping immediate `/user/collect_automatically` runs for the same user while preserving existing schedule dedupe.
11. Hotfix validation: focused scheduler regression suite passed with 51 passed and 0 failed.

## Progress Snapshot

1. Completed: first platform-infrastructure blocker slice C-2.
2. Completed: security dependency freshness and vulnerability minimum-floor update slice.
3. Completed: remaining Track 1 runtime/deploy bundle.
4. Completed: security hardening bundle.
5. Completed: tester regression gate (243 passed, 2 env-specific failures).
6. Completed: QA readiness decision (conditional pass).
7. Completed: tester deterministic Windows symlink test remediation.
8. Completed: final QA confirmation.
9. Completed: sequence remaining unresolved open points.
10. Completed: remaining Track 1 backend reliability bundle.
11. Completed: Track 2 api-surface hardening.
12. Completed: Track 3 platform runtime observability hardening.
13. Completed: Track 4 security tail.
14. Completed: final tester gate.
15. Completed: final QA acceptance.
16. Completed: documentation synchronization and closure.