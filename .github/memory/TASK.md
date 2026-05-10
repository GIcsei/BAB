# ACTIVE TASK

- Task ID: BAB-CI-RECOVERY-2026-05-10
- Request: Perform full code review verification by running full pytest, bandit, and mypy; recover failing CI/CD gates.
- Owner: scrum-master
- Stage: done
- Priority: high
- Started: 2026-05-10

## Acceptance Criteria

- [x] Run CI-equivalent full pytest command and capture first concrete failure.
- [x] Run bandit and capture blocking findings.
- [x] Run mypy and capture blocking findings.
- [x] Implement minimal behavior-preserving fixes for all blockers.
- [x] Re-run pytest, bandit, and mypy until all three gates pass.
- [x] Complete tester and QA review handoffs for closure.

## Evidence

- Tester verification run: `uv run pytest -v --maxfail=1 --cov=app --cov-fail-under=70 --cov-report=xml:coverage.xml --cov-report=term-missing --cov-report=html:htmlcov --html=reports/pytest-report.html --self-contained-html` -> failed at `tests/functionaltest/test_feature_enhancements.py` (expected 200, got 400).
- Bandit run: `uv run bandit -r app -ll` -> failed with B310 medium finding in `app/core/health.py`.
- Mypy run: `uv run mypy app` -> failed with `no-untyped-call` in `app/core/firestore_handler/Utils.py`.
- Implemented fix: `app/core/netbank/getReport.py` updated to return `False` on exception in `_handle_already_logged_in_Selenium`.
- Full tests passed: `uv run pytest -q` -> `625 passed, 2 skipped, 1 warning`.
- CI-style pytest passed: `uv run pytest -v --maxfail=1 --cov=app --cov-fail-under=70 --cov-report=xml:coverage.xml --cov-report=term-missing --cov-report=html:htmlcov --html=reports/pytest-report.html --self-contained-html` -> `625 passed, 2 skipped, 1 warning`.
- Bandit passed: `uv run bandit -r app -ll` -> no issues identified.
- Mypy passed: `uv run mypy app` -> success in 41 source files.
- Tester gate passed and QA review passed for closure.
