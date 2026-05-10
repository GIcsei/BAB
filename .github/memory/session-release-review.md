# Session: Release Stability Sprint Planning (2026-05-10)

## User Request
"Perform a review of the codebase with the whole team! ... Consider the following bugs: [7 issues]. In this phase, do only planning and update the relevant .md files! Plan .md files with phases, where each phase is gonna be one branch!"

## Execution Summary

### Delegations
1. **tech-lead** → Analyzed codebase for 7 issues, created phased sequencing plan with 4 phases, identified dependencies, ownership, and risks.
2. **documentation-writer** → Created `.github/memory/RELEASE_PLAN.md`, updated `.github/TODO.md` (E7 epic + 4 tasks), updated `plan.md` and `active-context.md` with phase tracking.

### Planning Output

#### 4 Phases Identified

| Phase | Branch | Owner | Issues | Pre-req | Status |
|-------|--------|-------|--------|---------|---------|
| 1 | `feature/consolidate-firestore-services` | backend-implementer | #3 (Firestore duplication) | – | not-started |
| 2 | `feature/improve-logging-auth-scheduler` | backend-implementer | #2, #1, #7 (Logging, Scheduler access, Token lifecycle) | Phase 1 | not-started |
| 3 | `feature/secure-parquet-streaming` | api-surface | #5, #6 (File exposure, Parquet streaming) | Phase 1 | not-started |
| 4 | `infra/fix-release-docker` | platform-infrastructure | #4 (CI/CD Docker release) | – (parallel) | not-started |

#### Execution Order
- Phase 1 → Phase 2 + Phase 3 in parallel → Phase 4 in parallel
- Total unblocking sequence: Phase 1 → (Phase 2, 3, 4 concurrent)

### Key Findings
- **Firestore Issue:** Two services (`DatabaseHandler.Database` + `FirestoreService`) wrap same REST API; consolidation unblocks scheduler resilience.
- **Scheduler Issue:** Token state not persisted across job runs; retry logic missing; needs Phase 1 consolidation first.
- **Token Lifecycle:** Logout clears local files but doesn't revoke Firebase tokens or clear `TokenService` registry.
- **Logging:** Needs structured context fields (user_id, correlation_id) across critical paths.
- **File Access:** Currently exposes all file types; should restrict to `.parquet` only.
- **Streaming:** New `GET /data/files/{filename}/stream` endpoint needed for large datasets.
- **CI/CD Docker:** Release job failing; needs secrets verification and end-to-end test.

### Files Created/Updated
- **Created:** `.github/memory/RELEASE_PLAN.md` — Full 4-phase plan with scope, blockers, and executive summary
- **Updated:** `.github/TODO.md` — Added E7 epic with T-07 through T-10 tasks
- **Updated:** `.github/memory/plan.md` — Added "Stable Release Execution (2026-05-10)" section
- **Updated:** `.github/memory/active-context.md` — Phase transitioned to "Release Stability Sprint"

### Status
✅ **Planning complete.** All 7 issues mapped to 4 phases with clear sequencing, ownership, and branch strategy. Phase 1 (backend-implementer) is unblocked and ready to start on Firestore consolidation.

### Next Steps
1. backend-implementer begins **Phase 1** on `feature/consolidate-firestore-services`
2. Upon Phase 1 completion, **Phase 2** (backend-implementer) and **Phase 3** (api-surface) proceed in parallel
3. **Phase 4** (platform-infrastructure) can start immediately if desired
4. Tester and qa-engineer provide validation gates before each phase merge

---

## Phase 2 Execution Update (2026-05-10)

- Implementation completed for T-08 in `app/main.py`, `app/application/services/token_service.py`, and `app/infrastructure/sched/scheduler.py`.
- Follow-up hardening run executed for two residual risks: relative-only persisted token expiry ambiguity and non-`fcntl` scheduler leader behavior.
- Tester peer-review reruns passed (focused 16 passed, broader targeted 78 passed, 0 failed).
- Security follow-up returned conditional pass with guardrail requirement for `APP_SCHEDULER_NO_FCNTL_ASSUME_LEADER` override governance.
- QA final Phase 2 decision: conditional pass, Phase 2 complete in sprint execution terms.
