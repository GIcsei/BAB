# ACTIVE TASK

- Task ID: BAB-FIRESTORE-TOKEN-EXPIRY-2026-05-14
- Request: Fix Firestore credential expiry after long inactive sessions that breaks scheduler OTP polling.
- Owner: scrum-master
- Stage: qa-conditional-pass
- Priority: high
- Started: 2026-05-14

## Acceptance Criteria

[x] Scheduler/user activation path refreshes expired Firestore token before query usage.
[x] Existing token-service behavior is preserved for non-expired tokens.
[x] Refresh-failure fallback behavior remains non-breaking (no new crash path).
- [x] Focused tester validation passes.
[x] QA readiness review completed.

## Evidence

- Implementation change: `app/application/services/token_service.py` now refreshes expired active-user tokens in `set_active_user` before setting active registry state.
- Test updates: `tests/unittest/test_query_handler.py` adds refresh-success and refresh-failure fallback coverage for expired tokens.
- Tester gate: `./.venv/Scripts/python.exe -m pytest tests/unittest/test_query_handler.py -q` -> 29 passed.
- Adjacent validation: `./.venv/Scripts/python.exe -m pytest tests/unittest/test_coverage_gaps_extended.py -q -k "token_service_relative_only_expiry_is_treated_as_expired or token_service_normalize_sets_absolute_expiry_from_refresh_relative"` -> 2 passed, 4 deselected.
- Integration validation: `./.venv/Scripts/python.exe -m pytest tests/integrationtest/test_query_handler_extended.py -q` -> 10 passed.
- QA gate: conditional pass with residual rollout-monitoring recommendation for refresh failures and scheduler OTP polling 401 trends.
