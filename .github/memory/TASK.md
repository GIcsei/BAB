# ACTIVE TASK

- Task ID: BAB-RELEASE-STABILITY-PHASE3-2026-05-10
- Request: Implement Release Stability Sprint Phase 3 (T-09 / issues #5, #6): secure parquet streaming and file access controls.
- Owner: api-surface
- Stage: qa-review
- Priority: high
- Started: 2026-05-10

## Acceptance Criteria

- [x] Inspect parquet access control and streaming validation surfaces.
- [x] Implement minimal API-surface hardening without contract drift.
- [x] Add/update focused tests for boundary and validation behavior.
- [x] Run targeted pytest validation.
- [x] Sync required orchestration memory and backlog artifacts.

## Evidence

- Phase 3 api-surface implementation completed with parquet-only listing, parquet filename enforcement, and secure stream endpoint.
- Focused validation command passed: `python -m pytest -q tests/functionaltest/test_data_plot_router.py tests/unittest/test_data_service.py` (24 passed).
- Tester peer review passed for Phase 3 parquet-only stream and file exposure changes.
