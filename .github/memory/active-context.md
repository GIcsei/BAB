# ACTIVE CONTEXT

## Current Focus
Add BAB version readout to `/health` and validate contract/docs.

## Current Phase
/health version readout (complete)

## Current Owner
scrum-master

## Next Handoff
none

## Blockers
- Residual risk: privileged Windows symlink branch remains skipped in non-elevated environments.
- Residual risk: `set_user_block_state` currently uses full-document write semantics and may overwrite non-blocking fields in `users/{user_id}` when populated documents exist.
- Residual risk: non-`fcntl` scheduler leadership now defaults to follower safety unless explicit env opt-in (`APP_SCHEDULER_NO_FCNTL_ASSUME_LEADER`) is configured for deterministic single-leader deployment.

## Notes
- **2026-05-10: `/health` now includes `version` in both ready (200) and not-ready (503) responses via api-surface implementation in `app/main.py`.**
- **2026-05-10: Tester gate passed for the health-version scope (`3 passed` endpoint tests + `10 passed` unit health tests).**
- **2026-05-10: Documentation updated in `docs/api.md` to reflect `version` presence for both 200 and 503 health responses.**
- **2026-05-10: Implemented CI recovery fix in `app/core/netbank/getReport.py` by returning `False` on exceptions in `_handle_already_logged_in_Selenium`, resolving failing unit test path.**
- **2026-05-10: Tester post-fix gate passed (`625 passed, 2 skipped, 1 warning`) for both full and CI-style pytest commands, plus bandit and mypy.**
- **2026-05-10: QA review passed for CI recovery scope with low residual risk note on mocked Selenium-path coverage.**
- **2026-05-10: Tester executed CI-equivalent verification and found three hard gate failures: Bandit B310 (`app/core/health.py`), mypy no-untyped-call (`app/core/firestore_handler/Utils.py`), and pytest status mismatch (`tests/functionaltest/test_feature_enhancements.py`).**
- **2026-05-10: Next implementation handoff is `backend-implementer` to remediate CI blockers, followed by `tester` re-run and `qa-engineer` review.**
- Product-owner clarified that open points include orchestration queue T-01..T-06 and unresolved findings in `.github/memory/TODO.md`.
- C-2 completed and config-verified: `FIREBASE_API_KEY` added to TrueNAS env template and compose environment.
- Web verification of package freshness completed; dependency minimums and lockfile were updated in a security-owned slice.
- Track 1 runtime/deploy bundle completed for C-1, C-3 short-term, H-1, M-7, and L-3.
- Security hardening bundle completed for C-4, H-2, H-3, H-4, H-5, H-7, H-8, M-2, and M-9 with focused tests.
- Tester gate executed: 243 passed, 2 failed (environment-specific symlink privilege constraint).
- QA review returned conditional pass and requested targeted tester remediation for Windows symlink test determinism.
- Tester remediation completed: symlink-hardening tests now deterministic with expected Windows privilege-aware skips.
- QA final confirmation returned conditional pass for completed slices.
- Tech-lead queued remaining unresolved sequence; backend-implementer Track 1 is next.
- Backend-implementer Track 1 completed for M-1, M-5, M-6, M-8, L-2, L-4, and L-5.
- API-surface Track 2 completed for M-3 and M-4.
- Platform-infrastructure Track 3 completed for M-10 and M-11.
- Security-engineer Track 4 completed with H-6 mitigation and focused tests.
- Final tester gate passed: 144 passed, 2 skipped, 0 failed.
- QA final acceptance: conditional pass for Linux/TrueNAS with residual risks documented.
- Documentation synchronization completed across README and docs surfaces.
- Delegation remains single-specialist per handoff with immediate memory synchronization.
- **2026-05-10: Phase 3 routed to `api-surface` for secure parquet streaming and file exposure hardening.**
- **2026-05-10: Phase 3 implementation landed and focused validation passed; awaiting tester review.**
- **2026-05-10: Phase 3 tester peer review passed; awaiting QA readiness review.**
- **2026-05-10: Phase 4 routed to `platform-infrastructure` for release workflow gating.**
- **2026-05-10: Phase 4 implementation landed and release workflow now waits for Docker publish before creating the GitHub release.**
- **2026-05-10: Phase 4 QA passed and the release workflow gate is accepted.**
- **2026-05-10: Tech-lead sequenced 7 open issues into Release Stability Sprint — 4 phases spanning backend, API, and infrastructure.**
- **7 issues grouped into 4 phases; Phase 1 unblocks Phase 2+3; Phase 4 runs independently.**
- **2026-05-10: Phase 1 completed by backend-implementer. Firestore user block/unblock writes consolidated into `FirestoreService.set_user_block_state` and login-service callers switched to that single surface with focused unit tests passing (42 passed).**
- **2026-05-10: Tester gate for Phase 1 passed in focused scope (`25 passed, 0 failed`) across Firestore service and registration service tests.**
- **2026-05-10: QA returned conditional pass for Phase 1 with follow-up recommendation to verify field-preservation semantics for populated `users/{user_id}` documents.**
- **2026-05-10: Phase 2 (T-08) implemented by backend-implementer for logging consistency/observability, token refresh reliability with expiration-aware normalization, and scheduler startup leadership bootstrap to reduce restore race conditions.**
- **2026-05-10: Focused Phase 2 validation passed: `27 passed` (`tests/integrationtest/test_query_handler_extended.py`, `tests/unittest/test_scheduler_extended.py`, `tests/functionaltest/test_main_startup.py`) plus adjacent compatibility checks `17 passed` (`tests/unittest/test_coverage_gaps_extended.py`, `tests/integrationtest/test_query_handler_coverage.py`).**
- **2026-05-10: Phase 2 follow-up hardening completed by backend-implementer for two residual risks: legacy relative-only token expiry ambiguity and non-`fcntl` multi-leader scheduling risk.**
- **2026-05-10: Follow-up focused validation passed: `16 passed` (`tests/unittest/test_coverage_gaps_extended.py`, `tests/unittest/test_scheduler_extended.py`).**
- **2026-05-10: Tester second-run peer review passed after hardening (`16 passed` focused + `78 passed` broader targeted regression, `0 failed`).**
- **2026-05-10: Security follow-up review confirmed legacy relative-expiry ambiguity closure and reduced non-`fcntl` multi-leader risk; conditional on deployment guardrail enforcement for `APP_SCHEDULER_NO_FCNTL_ASSUME_LEADER`.**
- **2026-05-10: QA final decision for Phase 2 is conditional pass; phase is complete for sprint execution with mandatory release-time guardrails for non-`fcntl` override governance.**
- **2026-05-10: Backend hotfix added per-user in-flight dedupe for immediate scheduler triggers so repeated `/user/collect_automatically` calls for the same user become safe no-op while a run is active, without creating duplicate schedules.**
- **2026-05-10: Tester validated hotfix scope with scheduler-focused regression suite (`51 passed, 0 failed`).**
