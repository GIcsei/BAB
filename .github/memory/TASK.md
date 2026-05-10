# ACTIVE TASK

- Task ID: BAB-OPEN-POINTS-EXECUTION-2026-05-08
- Request: Check memory and implement every open point with team delegation, package-freshness vulnerability checks, and testing evidence.
- Owner: scrum-master
- Stage: done
- Priority: high
- Started: 2026-05-08
- Finished: 2026-05-08

## Acceptance Criteria

- [x] Convert all open points from `.github/TODO.md` and `.github/memory/TODO.md` into delegated, owned work slices.
- [x] Apply code/config/doc changes for each accepted open point without breaking API contracts.
- [x] Perform web-based package freshness checks before dependency-security decisions.
- [x] Execute focused tests for changed areas and record results.
- [x] Complete tester and QA gates for residual risk.
- [x] Sync orchestration memory and TODO artifacts after each meaningful handoff.

## Evidence

- Product-owner clarification accepted with ownership grouping and first-step sequence.
- Tech-lead sequence accepted: first implementation slice is C-2 by `platform-infrastructure` with startup smoke validation.
- C-2 implemented: `truenas.env.example` and `docker/docker-compose.truenas.yml` now wire `FIREBASE_API_KEY`; compose config render confirmed variable propagation.
- Dependency freshness/vulnerability slice completed: `pyproject.toml` minimums hardened, legacy `parquet` removed, `uv.lock` regenerated, focused pytest passed.
- Track 1 runtime/deploy hardening bundle completed: `.env` untracked safely, workers pinned to 1 in runtime surfaces, Selenium URL env-wired, TrueNAS remap start behavior made explicit, and env template retention setting documented.
- Security hardening bundle completed with tests: auth endpoint rate limiting, credential file handling hardening, redirect auth safety, input validation bounds, and sanitized error responses.
- Tester gate executed across changed surfaces: 243 passed, 2 failed due Windows symlink privilege constraint in symlink-hardening tests; QA review queued.
- QA decision: conditional pass for Linux/TrueNAS target, with required targeted tester remediation for deterministic Windows symlink test behavior.
- Tester remediation complete: `tests/unittest/test_security_hardening.py` now privilege-aware; focused rerun result 17 passed, 2 skipped, 0 failed.
- QA final confirmation: conditional pass maintained after remediation; residual risk documented for skipped privileged Windows branch.
- Tech-lead produced remaining unresolved implementation sequence (backend, api-surface, platform, security tail).
- Backend Track 1 complete: timezone/deprecation fixes, cross-platform file-time consistency, mutable-default fix, safer report formatter defaults/guard, exception-path cleanup, timezone-aware health timestamp, and dead code directory removal.
- API Track 2 complete: request-body size limit middleware and explicit CORS method allowlist with focused functional tests passing.
- Platform Track 3 complete: log rotation configurability and Selenium health component readiness with focused health/logging tests passing.
- Security Track 4 complete: header-first Firebase API-key transport mitigation with compatibility fallback and focused security tests passing.
- Final tester gate result: 144 passed, 2 skipped, 0 failed across targeted changed areas.
- Final QA acceptance: conditional pass for Linux/TrueNAS target with residual risk notes captured.
- Documentation synchronization completed across README and docs surfaces.
