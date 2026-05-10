# Release Stability Sprint — Phased Execution Plan

**Status:** In Progress (Phases 1 and 2 complete)  
**Date Started:** 2026-05-10  
**Target Completion:** TBD (sequential + parallel phases)

---

## Executive Summary

7 open issues consolidated into 4 distinct phases spanning backend services, API surface, and infrastructure. Phase 1 unblocks Phases 2 and 3 to execute in parallel. Phase 4 runs independently.

| Phase | Branch | Owner | Status | Pre-req |
|-------|--------|-------|--------|---------|
| 1 | `feature/consolidate-firestore-services` | backend-implementer | completed (QA conditional pass) | – |
| 2 | `feature/improve-logging-auth-scheduler` | backend-implementer | completed (QA conditional pass after second-run peer review) | Phase 1 |
| 3 | `feature/secure-parquet-streaming` | api-surface | not-started | Phase 1 |
| 4 | `infra/fix-release-docker` | platform-infrastructure | not-started | – (parallel) |

---

## Phase 1: Consolidate Firestore Services

**Owner:** backend-implementer  
**Branch:** `feature/consolidate-firestore-services`  
**Status:** completed (QA conditional pass)  
**Pre-requisites:** None

### Issues Addressed
- **#3** — Eliminate Firestore service duplication in `app/core/firestore_handler/` and `app/services/`

### Scope
- Identify and consolidate duplicate service patterns
- Preserve API contracts
- Update all callers without changing behavior
- Add targeted tests for consolidated surface

### Deliverable
Merged PR reducing Firestore handler coupling and establishing single source of truth for database operations.

### Validation Outcome
- Implementation validation: `python -m pytest -q tests/unittest/test_firestore_service.py tests/unittest/test_registration_service.py tests/unittest/test_login_service.py tests/unittest/test_login_service_extended.py` (42 passed).
- Tester gate: `python -m pytest -q tests/unittest/test_firestore_service.py tests/unittest/test_registration_service.py` (25 passed).
- QA gate: Conditional pass with follow-up recommendation to verify field-preservation semantics for populated `users/{user_id}` documents.

---

## Phase 2: Improve Logging, Auth, and Scheduler

**Owner:** backend-implementer  
**Branch:** `feature/improve-logging-auth-scheduler`  
**Status:** completed (QA conditional pass after second-run peer review)  
**Pre-requisites:** Phase 1 complete

### Issues Addressed
- **#2** — Improve logging consistency and debug observability
- **#1** — Strengthen token refresh reliability and expiration handling
- **#7** — Fix scheduler initialization race and multi-worker startup

### Scope
- Standardize logging across services (post-Firestore consolidation)
- Harden JWT token lifecycle with defensive checks
- Ensure scheduler idempotency and clean restore on worker restart
- Behavior-preserving refactors only

### Deliverable
Merged PR with improved reliability across authentication, scheduling, and observability surfaces.

### Validation Outcome
- Implementation validation: `python -m pytest -q tests/integrationtest/test_query_handler_extended.py tests/unittest/test_scheduler_extended.py tests/functionaltest/test_main_startup.py` (27 passed).
- Compatibility validation: `python -m pytest -q tests/unittest/test_coverage_gaps_extended.py tests/integrationtest/test_query_handler_coverage.py` (17 passed, 1 warning).
- Follow-up hardening validation: `pytest -q tests/unittest/test_coverage_gaps_extended.py tests/unittest/test_scheduler_extended.py` (16 passed).
- Tester second-run peer review: focused + broader targeted reruns passed (16 passed + 78 passed, 0 failed).
- Security follow-up: conditional pass; legacy relative-expiry ambiguity closed, non-`fcntl` multi-leader risk reduced via follower-safe default and explicit override.
- QA final decision: conditional pass with release-time guardrails for non-`fcntl` override governance.

---

## Phase 3: Secure Parquet Streaming and File Exposure

**Owner:** api-surface  
**Branch:** `feature/secure-parquet-streaming`  
**Status:** not-started  
**Pre-requisites:** Phase 1 complete

### Issues Addressed
- **#5** — Fix file exposure and access control on parquet download endpoints
- **#6** — Improve parquet streaming reliability and request/response validation

### Scope
- Add user boundary checks to file access
- Validate streaming payload integrity
- Ensure OpenAPI contracts match runtime validation
- Cover with integration tests for boundary cases

### Deliverable
Merged PR hardening API surface and file access controls.

---

## Phase 4: Fix Release Docker and CI/CD

**Owner:** platform-infrastructure  
**Branch:** `infra/fix-release-docker`  
**Status:** not-started  
**Pre-requisites:** None (parallel execution)

### Issues Addressed
- **#4** — Fix Docker build, layer caching, and CI/CD release workflow

### Scope
- Diagnose and fix Docker build failures
- Optimize layer caching for release builds
- Ensure CI/CD passes all targets on tagged release
- Test across Linux, TrueNAS, and Windows environments

### Deliverable
Merged PR enabling clean release builds and artifact promotion.

---

## Execution Sequence

```
START
  ├─ Phase 1 (backend-implementer)
  │  └─ DONE?
  │     ├─ Phase 2 (backend-implementer) ──┐
  │     └─ Phase 3 (api-surface)      ┤ Parallel
  │           └─ DONE? ────────────────┘
  │
  └─ Phase 4 (platform-infrastructure) [parallel from START]
```

### Timeline
1. **Phase 1** starts immediately (no dependencies).
2. **Phases 2 & 3** start after Phase 1 completes (both can run in parallel).
3. **Phase 4** can start anytime; does not depend on other phases.
4. **Release gate** occurs after all phases complete and tester/qa validate.

---

## Memory and Handoff Protocol

- Each phase maintains a PR branch with targeted commits.
- Phase owner includes tester and qa-engineer for validation.
- After merge, owner updates `.github/memory/active-context.md` with next phase.
- `.github/memory/plan.md` records completion and re-sequences remaining work.

---

## Delivery Criteria

- All issues addressed and tested
- No API contract breaks
- Pytest regression suite passes
- QA readiness gate cleared
- Documentation synchronized

---

**Last Updated:** 2026-05-10  
**Next Review:** Before release promotion (resolve/accept Phase 1 field-preservation residual risk and enforce Phase 2 non-`fcntl` override guardrails)
