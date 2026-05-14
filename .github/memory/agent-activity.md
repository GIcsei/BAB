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

### 2026-05-10 | backend-implementer

- Scope: Release Stability Sprint Phase 1 (T-07 / issue #3) to consolidate Firestore write operations and remove service-layer duplication.
- Outcome: Added consolidated Firestore user block-state method and updated login/registration callers to use the single Firestore service surface.
- Evidence: Updated `app/core/firestore_handler/FirestoreService.py`, `app/services/login_service.py`, `tests/unittest/test_firestore_service.py`, `tests/unittest/test_registration_service.py`; ran `python -m pytest -q tests/unittest/test_firestore_service.py tests/unittest/test_registration_service.py tests/unittest/test_login_service.py tests/unittest/test_login_service_extended.py` (42 passed).
- Next handoff: `backend-implementer` for T-08 and `api-surface` for T-09.

### 2026-05-10 | tester

- Scope: Execute focused Phase 1 regression gate for Firestore consolidation and affected auth caller tests only.
- Outcome: Approved Phase 1 tester gate with no test-file changes required.
- Evidence: Ran `python -m pytest -q tests/unittest/test_firestore_service.py tests/unittest/test_registration_service.py` (25 passed, 0 failed, 0 skipped); verified call sites in `app/services/login_service.py` use `set_user_block_state`.
- Next handoff: `qa-engineer` for readiness assessment on residual semantics risk.

### 2026-05-10 | qa-engineer

- Scope: Assess Phase 1 release readiness based on implementation and focused tester evidence.
- Outcome: Conditional pass for Phase 1; residual risk recorded regarding potential overwrite semantics on populated `users/{user_id}` documents.
- Evidence: Reviewed `app/core/firestore_handler/FirestoreService.py`, `app/services/login_service.py`, and focused pytest evidence (42 passed + 25 passed).
- Next handoff: `scrum-master` to keep later phases queued and track field-preservation follow-up before release promotion.

### 2026-05-10 | backend-implementer

- Scope: Release Stability Sprint Phase 2 (T-08 / issues #2, #1, #7) for logging consistency/observability, token refresh reliability with expiration handling, and scheduler startup reliability.
- Outcome: Implemented module-level startup logger consistency in `app/main.py`, expiration-aware token normalization/fallback safeguards in `app/application/services/token_service.py`, and scheduler startup leadership bootstrap in `app/infrastructure/sched/scheduler.py` to reduce restore race windows.
- Evidence: Updated `app/main.py`, `app/application/services/token_service.py`, `app/infrastructure/sched/scheduler.py`, `tests/integrationtest/test_query_handler_extended.py`, `tests/unittest/test_scheduler_extended.py`, `tests/functionaltest/test_main_startup.py`; ran `python -m pytest -q tests/integrationtest/test_query_handler_extended.py tests/unittest/test_scheduler_extended.py tests/functionaltest/test_main_startup.py` (27 passed) and `python -m pytest -q tests/unittest/test_coverage_gaps_extended.py tests/integrationtest/test_query_handler_coverage.py` (17 passed, 1 warning).
- Next handoff: `tester` for focused regression gate confirmation on Phase 2 scope.

### 2026-05-10 | backend-implementer

- Scope: Phase 2 follow-up hardening only for token-freshness ambiguity on legacy persisted relative-expiry tokens and non-`fcntl` scheduler leadership safety.
- Outcome: Hardened token expiry evaluation to treat relative-only persisted metadata as expired while still normalizing fresh refresh responses to absolute expiry; hardened non-`fcntl` scheduler path to safe follower mode by default with explicit opt-in leader fallback and exposed `is_leader` probe for deterministic startup behavior.
- Evidence: Updated `app/application/services/token_service.py`, `app/infrastructure/sched/scheduler.py`, `tests/unittest/test_coverage_gaps_extended.py`, `tests/unittest/test_scheduler_extended.py`; ran `(.venv activated) pytest -q tests/unittest/test_coverage_gaps_extended.py tests/unittest/test_scheduler_extended.py` (16 passed).
- Next handoff: `tester` for focused regression confirmation on Phase 2 residual-risk closure.

### 2026-05-10 | tester

- Scope: Independent second-run peer review for Phase 2 hardening and broader targeted regression confidence.
- Outcome: Passed focused and broader targeted Phase 2 reruns with no failures.
- Evidence: Ran `pytest -q -ra tests/unittest/test_coverage_gaps_extended.py tests/unittest/test_scheduler_extended.py` (16 passed) and broader targeted set (`tests/unittest/test_scheduler.py`, `tests/unittest/test_scheduler_coverage.py`, `tests/unittest/test_scheduler_worker.py`, `tests/unittest/test_token_registry.py`, `tests/integrationtest/test_remaining_coverage.py`) for 78 passed.
- Next handoff: `security-engineer` for follow-up risk closure review.

### 2026-05-10 | security-engineer

- Scope: Follow-up security review of Phase 2 hardening changes for token expiry handling and non-`fcntl` leader behavior.
- Outcome: Conditional pass; legacy relative-expiry ambiguity closed and non-`fcntl` risk reduced with explicit override guardrail retained.
- Evidence: Reviewed `app/application/services/token_service.py` and `app/infrastructure/sched/scheduler.py`; ran `pytest -q -ra tests/unittest/test_coverage_gaps_extended.py tests/unittest/test_scheduler_extended.py tests/unittest/test_token_registry.py` (33 passed).
- Next handoff: `qa-engineer` for final readiness adjudication.

### 2026-05-10 | qa-engineer

- Scope: Final Phase 2 readiness adjudication after second-run implementation and peer-review gates.
- Outcome: Conditional pass; Phase 2 complete for sprint execution with mandatory release-time guardrails on non-`fcntl` override governance.
- Evidence: Accepted tester and security follow-up evidence (focused 16 passed + broader targeted 78 passed, 0 failed; security conditional pass).
- Next handoff: `scrum-master` to retain Phase 3 and Phase 4 queue order and carry guardrails into release governance.

### 2026-05-10 | backend-implementer

- Scope: Hotfix scheduler behavior for repeated same-user immediate trigger requests (`/user/collect_automatically`) to prevent overlapping runs.
- Outcome: Added in-flight per-user dedupe in scheduler spawn path; duplicate immediate triggers for active user runs now return success as no-op and do not spawn concurrent duplicates.
- Evidence: Updated `app/infrastructure/sched/scheduler.py` and `tests/unittest/test_scheduler_extended.py`; focused scheduler validation run reported 51 passed.
- Next handoff: `tester` for independent confirmation.

### 2026-05-10 | tester

- Scope: Independent focused regression validation for scheduler duplicate-trigger hotfix behavior.
- Outcome: Approved hotfix scope; same-user duplicate immediate trigger overlap prevented while allowing subsequent run after prior completion.
- Evidence: Ran `pytest -q -ra tests/unittest/test_scheduler_extended.py tests/unittest/test_scheduler.py tests/unittest/test_scheduler_worker.py tests/unittest/test_scheduler_coverage.py` (51 passed, 0 failed).
- Next handoff: `scrum-master` to report outcome and keep Phase 3/4 queue unchanged.

### 2026-05-10 | scrum-master

- Scope: Start Release Stability Sprint Phase 3 handoff for secure parquet streaming and file exposure.
- Outcome: Routed the api-surface slice after checking the current `/data` router and service boundary plus current FastAPI/OWASP file-handling guidance; Phase 3 is now owned by api-surface.
- Evidence: Reviewed `.github/memory/RELEASE_PLAN.md`, `.github/memory/TODO.md`, `.github/memory/active-context.md`, `app/routers/data_plot.py`, `app/services/data_service.py`, `tests/functionaltest/test_data_plot_router.py`; web-checked FastAPI custom response docs and OWASP path traversal guidance.
- Next handoff: `api-surface` implementation.

### 2026-05-10 | api-surface

- Scope: Implement Phase 3 parquet-only file exposure and secure stream route.
- Outcome: Added parquet-only file listing and filename validation, a shared safe resolved file-path helper, and a validated stream endpoint for authenticated parquet downloads.
- Evidence: Updated `app/routers/data_plot.py`, `app/services/data_service.py`, `tests/functionaltest/test_data_plot_router.py`, and `tests/unittest/test_data_service.py`; ran `python -m pytest -q tests/functionaltest/test_data_plot_router.py tests/unittest/test_data_service.py` (24 passed).
- Next handoff: `tester` for broader regression review.

### 2026-05-10 | platform-infrastructure

- Scope: Narrow runtime image pin update for Selenium Edge standalone in Docker/TrueNAS compose definitions.
- Outcome: Updated Selenium image tag from `selenium/standalone-edge:144.0-20260202` to `selenium/standalone-edge:146.0-20260404` in both runtime compose files; no app/service code changes.
- Evidence: Updated `docker/docker-compose.yml`, `docker/docker-compose.truenas.yml`, and validated with `docker compose -f docker/docker-compose.yml config` plus `docker compose -f docker/docker-compose.truenas.yml config` (with placeholder env interpolation values).
- Next handoff: `scrum-master` to merge runtime pin bump and continue planned release flow.

### 2026-05-10 | backend-implementer

- Scope: Implement minimal, behavior-preserving fixes for three verified CI blockers (Bandit B310 in health probe, mypy no-untyped-call in firestore Utils, and functional regression for CSV/JSON data endpoints).
- Outcome: Replaced unsafe urllib probe with timeout-bound requests call, resolved typed-context mypy blocker on redirect auth stripping call, restored CSV/JSON support for preview/series/list while keeping parquet-only stream contract.
- Evidence: Updated `app/core/health.py`, `app/core/firestore_handler/Utils.py`, `app/routers/data_plot.py`, `app/services/data_service.py`, `tests/unittest/test_data_service.py`; ran `uv run pytest tests/functionaltest/test_feature_enhancements.py -q` (28 passed), `uv run bandit -q -r app/core/health.py` (B310 cleared; only B112 low remains), `uv run mypy app/core/firestore_handler/Utils.py` (clean), plus focused and CI-style checks (`test_data_plot_router.py`, `test_data_service.py`, `ruff`, `black --check`, `mypy app`) all passing.
- Next handoff: `tester` for optional broader regression gate if full-suite rerun is required.

### 2026-05-10 | tester

- Scope: Peer-review regression pass for Phase 3 parquet-only file exposure and stream route.
- Outcome: Passed; no concrete defect found and the router/service boundary stayed internally consistent.
- Evidence: Reviewed `app/routers/data_plot.py` and `app/services/data_service.py`; reran `python -m pytest -q tests/functionaltest/test_data_plot_router.py tests/unittest/test_data_service.py` (24 passed).
- Next handoff: `qa-engineer` for release readiness review.

### 2026-05-10 | api-surface

- Scope: Phase 3 parquet streaming and file exposure hardening in `app/routers/data_plot.py` and `app/services/data_service.py`.
- Outcome: Routed `/data/files/{filename}/stream` through a parquet-only service resolver, preserved auth and user-boundary checks, and added focused coverage for the stream 404 path plus the parquet-only resolver rejection.
- Evidence: Updated `app/routers/data_plot.py`, `app/services/data_service.py`, `tests/functionaltest/test_data_plot_router.py`, and `tests/unittest/test_data_service.py`; ran `pytest -q tests/functionaltest/test_data_plot_router.py tests/unittest/test_data_service.py` (24 passed).
- Next handoff: `tester` for optional broader regression.

### 2026-05-10 | platform-infrastructure

- Scope: Phase 4 release workflow gating in `.github/workflows/release.yml`.
- Outcome: Added a hard dependency so GitHub release publication waits for Docker image publishing.
- Evidence: Updated `.github/workflows/release.yml`; validated with YAML parse check confirming `release.needs == ['validate', 'docker']`.
- Next handoff: `qa-engineer` for release-readiness review.

### 2026-05-10 | qa-engineer

- Scope: Final Phase 4 release workflow readiness review.
- Outcome: Approved the release gate change; no blocking workflow-order defect remains.
- Evidence: Reviewed `.github/workflows/release.yml`, `docker/Dockerfile`, and the YAML parse check result; accepted the `release.needs == ['validate', 'docker']` gate.
- Next handoff: `scrum-master` to close the sprint and promote release when ready.

### 2026-05-10 | tester

- Scope: Execute full CI-equivalent verification for user-reported CI/CD failure using pytest, bandit, and mypy with no code edits.
- Outcome: Found three blocking failures across all required gates.
- Evidence: Ran `uv run pytest -v --maxfail=1 --cov=app --cov-fail-under=70 --cov-report=xml:coverage.xml --cov-report=term-missing --cov-report=html:htmlcov --html=reports/pytest-report.html --self-contained-html` (failed at `tests/functionaltest/test_feature_enhancements.py`, expected 200 got 400), `uv run bandit -r app -ll` (failed with B310 at `app/core/health.py`), and `uv run mypy app` (failed with `no-untyped-call` at `app/core/firestore_handler/Utils.py`).
- Next handoff: `backend-implementer` to remediate CI blockers, then `tester` for full re-run.

### 2026-05-10 | tester

- Scope: Post-fix CI verification gate for user-requested full review run.
- Outcome: Passed all requested gates.
- Evidence: Ran `uv run pytest -q` (625 passed, 2 skipped, 1 warning), CI-style pytest command with coverage (`625 passed, 2 skipped, 1 warning`, coverage above threshold), `uv run bandit -r app -ll` (no issues identified), and `uv run mypy app` (success in 41 files).
- Next handoff: `qa-engineer` for readiness review.

### 2026-05-10 | qa-engineer

- Scope: Readiness review for CI recovery fix scope.
- Outcome: Pass with low residual risk note.
- Evidence: Reviewed `app/core/netbank/getReport.py` exception-path fix and accepted tester gate evidence for pytest, bandit, and mypy.
- Next handoff: `scrum-master` for closure.

### 2026-05-10 | api-surface

- Scope: Add BAB version readout to `GET /health` without changing existing readiness/status behavior.
- Outcome: Updated not-ready health payload to include `version`, making the response contract consistent across ready and not-ready states.
- Evidence: Updated `app/main.py`, `tests/functionaltest/test_main.py`, and `tests/functionaltest/test_feature_enhancements.py`; ran `uv run pytest tests/functionaltest/test_main.py -k health tests/functionaltest/test_feature_enhancements.py -k health tests/unittest/test_health.py` (16 passed).
- Next handoff: `tester` for independent gate.

### 2026-05-10 | tester

- Scope: Independent focused validation for `/health` version-readout change.
- Outcome: Pass; verified `version` appears in both ready and not-ready `/health` responses while status behavior remains unchanged.
- Evidence: Ran `uv run pytest tests/functionaltest/test_main.py::test_health_not_ready_returns_503 tests/functionaltest/test_feature_enhancements.py::TestHealthEndpoint::test_health_ready_includes_version_and_uptime tests/functionaltest/test_feature_enhancements.py::TestHealthEndpoint::test_health_not_ready_includes_version_and_omits_uptime` (3 passed) and `uv run pytest tests/unittest/test_health.py` (10 passed).
- Next handoff: `documentation-writer` for user-visible contract note.

### 2026-05-10 | documentation-writer

- Scope: Document `/health` version-readout contract.
- Outcome: Updated API docs to state that both 200 and 503 health responses include `version`, and clarified uptime is only present when ready.
- Evidence: Updated `docs/api.md` (health response examples and operational note).
- Next handoff: `scrum-master` to close task.

### 2026-05-14 | platform-infrastructure

- Scope: Fix Firestore authentication expiry in long-running inactive sessions impacting scheduler OTP polling.
- Outcome: Updated token activation path to refresh expired active-user tokens before query use, with safe fallback if refresh fails.
- Evidence: Updated `app/application/services/token_service.py` and `tests/unittest/test_query_handler.py`; validation reported `tests/unittest/test_query_handler.py` passing in focused scope.
- Next handoff: `tester` for independent regression verification.

### 2026-05-14 | tester

- Scope: Validate token-expiry fix and adjacent token/query handler behavior.
- Outcome: Pass; focused and adjacent test slices succeeded with no production code changes required.
- Evidence: Ran `./.venv/Scripts/python.exe -m pytest tests/unittest/test_query_handler.py -q` (29 passed), `./.venv/Scripts/python.exe -m pytest tests/unittest/test_coverage_gaps_extended.py -q -k "token_service_relative_only_expiry_is_treated_as_expired or token_service_normalize_sets_absolute_expiry_from_refresh_relative"` (2 passed), and `./.venv/Scripts/python.exe -m pytest tests/integrationtest/test_query_handler_extended.py -q` (10 passed).
- Next handoff: `qa-engineer` for readiness adjudication.

### 2026-05-14 | qa-engineer

- Scope: Readiness review for Firestore token-expiry fix affecting scheduler OTP polling path.
- Outcome: Conditional pass for merge/release based on implementation and test evidence.
- Evidence: Reviewed `app/application/services/token_service.py` and `tests/unittest/test_query_handler.py`; accepted tester evidence (`29 passed` + `10 passed` for query-handler scopes).
- Next handoff: `scrum-master` to close with rollout monitoring guidance.
