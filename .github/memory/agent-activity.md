# AGENT ACTIVITY LOG

Use this file as the durable summary surface for delegated work.

## Entry Format

- Date:
- Agent:
- Scope:
- Outcome:
- Evidence:
- Next handoff:

## Entries

### 2026-05-08 | scrum-master

- Scope: Refactor `.github` from a frontend-oriented agent stack to a backend-only BAB orchestration system.
- Outcome: Replaced the agent roster, routing guidance, memory/TODO surfaces, and orchestration framing with BAB-specific ownership boundaries.
- Evidence: Updated `.github/agents/`, `.github/TODO.md`, and `.github/memory/` live state files.
- Next handoff: Run one real backend task through the refreshed workflow to validate routing quality.

### 2026-05-08 | product-owner

- Scope: Clarify what “implement every open point” covers across orchestration TODOs and unresolved audit findings.
- Outcome: Produced ownership-grouped execution scope and smallest-first sequence recommendation.
- Evidence: Reviewed `.github/memory/TODO.md`, `.github/TODO.md`, `.github/memory/active-context.md`, `.github/memory/session-state.json`, `.github/memory/plan.md`, `.github/memory/TASK.md`.
- Next handoff: `tech-lead` to define the first narrow implementation slice and acceptance checks.

### 2026-05-08 | tech-lead

- Scope: Define the smallest safe first implementation slice from open-point backlog.
- Outcome: Approved Track 1 as C-2 only, assigning `platform-infrastructure` to wire `FIREBASE_API_KEY` in TrueNAS env and compose files with smoke validation.
- Evidence: Reviewed `.github/memory/TODO.md`, `.github/TODO.md`, and delegation contract requirements.
- Next handoff: `platform-infrastructure` implementation.

### 2026-05-08 | platform-infrastructure

- Scope: Implement C-2 only by wiring `FIREBASE_API_KEY` for TrueNAS deployment surfaces.
- Outcome: Added `FIREBASE_API_KEY` to env template and compose app environment; config render confirmed propagation.
- Evidence: Updated `truenas.env.example` and `docker/docker-compose.truenas.yml`; executed compose config verification.
- Next handoff: `security-engineer` for dependency freshness and vulnerability-check step.

### 2026-05-08 | security-engineer

- Scope: Execute dependency freshness plus vulnerability remediation for direct runtime dependencies with minimal behavioral risk.
- Outcome: Raised minimum versions to advisory-fixed floors for vulnerable packages, removed legacy `parquet` dependency, regenerated lockfile, and passed focused unit validation.
- Evidence: Updated `pyproject.toml` and `uv.lock`; executed `uv run pytest tests/unittest/test_data_service.py -q` (5 passed).
- Next handoff: `qa-engineer` to run broader regression/security test sweep if required.

### 2026-05-08 | platform-infrastructure

- Scope: Implement Track 1 remaining runtime/deploy items C-1, C-3, H-1, M-7, and L-3 with minimal behavior-preserving diffs.
- Outcome: Untracked `.env` with safe template handling, pinned runtime workers to one where needed, switched Selenium endpoint to `SELENIUM_REMOTE_URL`, enforced TrueNAS root start for UID/GID remap flow, and documented optional unregister deletion days setting.
- Evidence: Updated `.gitignore`, `.env.example`, `docker/Dockerfile`, `docker/docker-compose.prod.yml`, `docker/docker-compose.truenas.yml`, `app/core/netbank/getReport.py`, and `truenas.env.example`; executed `docker compose --env-file truenas.env.example -f docker/docker-compose.truenas.yml config` and `pytest -q tests/unittest/test_scheduler_extended.py` (7 passed).
- Next handoff: `qa-engineer` for regression/risk verification of combined runtime deploy slice.

### 2026-05-08 | security-engineer

- Scope: Implement security hardening bundle C-4, H-2, H-3, H-4, H-5, H-7/H-8, M-2, and M-9 with minimal behavior change.
- Outcome: Added auth endpoint rate limiting, per-request secure temporary auth token files, restrictive file permissions on token/deletion/download paths, cross-domain Authorization stripping on redirects, schema input bounds for credentials/passwords, and sanitized login/register generic error mapping.
- Evidence: Updated `app/core/rate_limit.py`, `app/routers/login.py`, `app/services/login_service.py`, `app/application/services/token_service.py`, `app/services/user_deletion_service.py`, `app/core/firestore_handler/Utils.py`, `app/core/netbank/getReport.py`, `app/schemas/login.py`, `app/schemas/netbank.py`, and focused tests under `tests/functionaltest/` and `tests/unittest/`; executed `.\.venv\Scripts\python.exe -m pytest -q tests/functionaltest/test_login_router.py tests/functionaltest/test_registration_router.py tests/functionaltest/test_feature_enhancements.py::TestPasswordReset tests/functionaltest/test_netbank_router.py tests/unittest/test_login_service_extended.py tests/unittest/test_user_deletion_service.py tests/unittest/test_query_handler.py tests/unittest/test_utils_extended.py tests/unittest/test_getreport_security.py` (99 passed).
- Next handoff: `qa-engineer` for residual regression review.

### 2026-05-08 | tester

- Scope: Execute mandatory regression gate across dependency/runtime/security changed surfaces without changing implementation.
- Outcome: Partial pass with strong coverage; 243 tests passed and 2 failed due Windows symlink privilege constraints in a hardening test path.
- Evidence: Ran focused functional, unit, and integration pytest command groups including auth/router/schema/token/getreport/security suites.
- Next handoff: `qa-engineer` for readiness decision and remediation routing.

### 2026-05-08 | qa-engineer

- Scope: Evaluate release readiness and residual risk for the combined dependency/runtime/security change set.
- Outcome: Conditional pass for Linux/TrueNAS target, with one required follow-up for deterministic Windows symlink test behavior.
- Evidence: Reviewed key changed runtime/security files and tester gate outputs.
- Next handoff: `tester` to make symlink-hardening tests privilege-aware and deterministic.

### 2026-05-08 | tester

- Scope: Apply QA-requested deterministic behavior to Windows symlink-hardening tests without changing production code.
- Outcome: Symlink-hardening tests now privilege-aware with deterministic skip behavior for expected Windows permission constraints.
- Evidence: Updated `tests/unittest/test_security_hardening.py`; reran focused test set with 17 passed and 2 skipped.
- Next handoff: `qa-engineer` for final confirmation.

### 2026-05-08 | qa-engineer

- Scope: Confirm readiness after tester remediation for deterministic Windows symlink test handling.
- Outcome: Conditional pass confirmed for completed slices; residual skipped privileged branch risk documented.
- Evidence: Reviewed updated symlink-hardening test and focused rerun outputs (17 passed, 2 skipped, 0 failed).
- Next handoff: `scrum-master` to continue remaining open-point execution.

### 2026-05-08 | tech-lead

- Scope: Define smallest safe sequence for remaining unresolved open points.
- Outcome: Ordered tracks by ownership with backend-implementer Track 1 prioritized.
- Evidence: Reviewed memory TODO backlog and active orchestration context.
- Next handoff: `backend-implementer` for Track 1 implementation.

### 2026-05-08 | backend-implementer

- Scope: Implement Track 1 unresolved backend reliability fixes.
- Outcome: Completed M-1, M-5, M-6, M-8, L-2, L-4, and L-5 with focused validation.
- Evidence: Updated core netbank/health/firestore files and focused tests; no diagnostics errors on touched files.
- Next handoff: `api-surface` for Track 2.

### 2026-05-08 | api-surface

- Scope: Implement Track 2 API hardening for request body size limits and explicit CORS methods.
- Outcome: Completed M-3 and M-4 with focused functional verification.
- Evidence: Updated `app/main.py` and related functional tests; focused CORS/body-limit tests passed.
- Next handoff: `platform-infrastructure` for Track 3.

### 2026-05-08 | platform-infrastructure

- Scope: Implement Track 3 runtime observability hardening.
- Outcome: Completed M-10 and M-11 with focused health/logging verification.
- Evidence: Updated logging and health/startup code plus focused tests with passing results.
- Next handoff: `security-engineer` for Track 4 security tail.

### 2026-05-08 | security-engineer

- Scope: Implement Track 4 security tail points.
- Outcome: Completed H-6 mitigation with header-first API key transport and compatibility fallback, with focused tests passing.
- Evidence: Updated security-related firestore handler/auth files and focused tests.
- Next handoff: `tester` for final gate.

### 2026-05-08 | tester

- Scope: Execute final tester gate across all changed tracks.
- Outcome: Approved with 144 passed, 2 skipped, 0 failed.
- Evidence: Ran focused functional and unit suites across security, API middleware, runtime health/logging, and reliability fixes.
- Next handoff: `qa-engineer` for final acceptance.

### 2026-05-08 | qa-engineer

- Scope: Final acceptance review for Tracks 1-4 and final tester gate.
- Outcome: Conditional pass approved for Linux/TrueNAS target with residual risks documented.
- Evidence: Reviewed key runtime/security files and final tester results.
- Next handoff: `documentation-writer` for final sync.

### 2026-05-08 | backend-implementer

- Scope: Implement remaining unresolved Track 1 reliability fixes in netbank, health, firestore auth, and dead-code cleanup with minimal diffs.
- Outcome: Completed M-1, M-5, M-6, M-8, L-2, L-4, and L-5 including targeted tests and empty `app/api` directory removal.
- Evidence: Updated `app/core/firestore_handler/User.py`, `app/core/netbank/getReport.py`, `app/core/netbank/utils.py`, `app/core/health.py`, `tests/unittest/test_getreport_security.py`, `tests/unittest/test_health.py`, and `tests/functionaltest/test_main.py`; removed empty `app/api` directory; ran focused pytest with 40 passed and 2 skipped.
- Next handoff: `tester` or `qa-engineer` for broader regression if requested.

### 2026-05-08 | api-surface

- Scope: Implement Track 2 API-surface points M-3 and M-4 in API-facing app wiring with minimal contract-preserving changes.
- Outcome: Added a safe HTTP request-body size limit middleware (1 MiB, returns 413) and replaced wildcard CORS methods with explicit GET/POST/PUT/DELETE; expanded focused functional tests for both behaviors.
- Evidence: Updated `app/main.py`, `tests/functionaltest/test_cors.py`, and `tests/functionaltest/test_main.py`; ran `./.venv/Scripts/python.exe -m pytest -q tests/functionaltest/test_main_startup.py tests/functionaltest/test_cors.py tests/functionaltest/test_main.py::test_request_body_size_limit_rejects_oversized_payload` (12 passed).
- Next handoff: `tester` for optional broader API regression sweep.

### 2026-05-08 | platform-infrastructure

- Scope: Implement Track 3 points M-10 and M-11 in logging and health/startup integration with deployment-safe behavior.
- Outcome: Added environment-configurable rotating log file parameters and introduced bounded Selenium readiness probing as a health component that never hard-fails startup.
- Evidence: Updated `app/core/logging_config.py`, `app/core/health.py`, `app/main.py`, `tests/unittest/test_logging_config.py`, `tests/unittest/test_health.py`, `tests/functionaltest/test_main.py`, and `tests/functionaltest/test_main_startup.py`; ran `./.venv/Scripts/python.exe -m pytest -q tests/unittest/test_logging_config.py tests/unittest/test_health.py tests/functionaltest/test_main_startup.py tests/functionaltest/test_main.py::test_health_not_ready_returns_503 tests/functionaltest/test_main.py::test_health_ready_returns_200 tests/functionaltest/test_main.py::test_health_components_present` (29 passed).
- Next handoff: `qa-engineer` for optional wider runtime regression sweep.

### 2026-05-08 | documentation-writer

- Scope: Sync README and docs with verified implementation/runtime behavior from the execution cycle.
- Outcome: Documented `.env` template handling, TrueNAS env additions (`FIREBASE_API_KEY`, `APP_UNREGISTER_DELETION_DAYS`, `SELENIUM_REMOTE_URL`), single-worker runtime pin, request-size and CORS method constraints, log-rotation env knobs, Selenium health component behavior, and Windows symlink-privilege test skip note.
- Evidence: Updated `README.md`, `docs/setup.md`, `docs/deployment.md`, `docs/api.md`, `docs/testing.md`, and `docs/architecture.md`.
- Next handoff: `scrum-master` to validate delegation contract response and merge doc-only delta.

### 2026-05-08 | scrum-master

- Scope: Finalize orchestration state after all open-point tracks, verification gates, and documentation sync.
- Outcome: Marked execution cycle complete with all planned tracks done and durable memory/TODO closure updates applied.
- Evidence: Updated `.github/memory/session-state.json`, `.github/memory/active-context.md`, `.github/memory/TASK.md`, `.github/memory/plan.md`, `.github/memory/TODO.md`, and `.github/TODO.md`.
- Next handoff: none.