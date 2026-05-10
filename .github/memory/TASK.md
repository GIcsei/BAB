# ACTIVE TASK

- Task ID: BAB-HEALTH-VERSION-2026-05-10
- Request: Add BAB version readout possibility to `/health`.
- Owner: scrum-master
- Stage: done
- Priority: high
- Started: 2026-05-10

## Acceptance Criteria

- [x] `/health` includes a `version` field in ready responses.
- [x] `/health` includes a `version` field in not-ready responses.
- [x] Existing health status behavior remains unchanged.
- [x] Focused tester validation passes.
- [x] API documentation reflects the new response detail.

## Evidence

- Implementation change: `app/main.py` now includes `version` in the 503 not-ready `/health` response payload while preserving existing status semantics.
- Test updates: `tests/functionaltest/test_main.py` and `tests/functionaltest/test_feature_enhancements.py` assert `version` presence for not-ready responses.
- Tester gate: `uv run pytest tests/functionaltest/test_main.py::test_health_not_ready_returns_503 tests/functionaltest/test_feature_enhancements.py::TestHealthEndpoint::test_health_ready_includes_version_and_uptime tests/functionaltest/test_feature_enhancements.py::TestHealthEndpoint::test_health_not_ready_includes_version_and_omits_uptime` -> 3 passed.
- Additional health unit validation: `uv run pytest tests/unittest/test_health.py` -> 10 passed.
- Documentation sync: `docs/api.md` updated to note `version` in both 200 and 503 `/health` responses.
