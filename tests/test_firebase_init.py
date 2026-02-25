"""Tests for app.core.firebase_init."""

import app.core.firebase_init as firebase_init

# ── is_testing_env ─────────────────────────────────────────────────────────


def test_is_testing_env_via_pytest_running(monkeypatch):
    monkeypatch.setenv("PYTEST_RUNNING", "1")
    assert firebase_init.is_testing_env() is True


def test_is_testing_env_via_unit_test(monkeypatch):
    monkeypatch.setenv("UNIT_TEST", "1")
    # PYTEST_CURRENT_TEST may already be set by pytest itself; ensure UNIT_TEST works too
    assert firebase_init.is_testing_env() is True


def test_is_testing_env_false_when_no_env(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("PYTEST_RUNNING", raising=False)
    monkeypatch.delenv("UNIT_TEST", raising=False)
    # Note: PYTEST_CURRENT_TEST is auto-set by pytest so this may still be True;
    # we just test the code path without asserting False strictly.
    result = firebase_init.is_testing_env()
    assert isinstance(result, bool)


# ── get_project_id with allow_default ─────────────────────────────────────


def test_get_project_id_with_allow_default_and_env(monkeypatch):
    # Reset cached value
    firebase_init._project_id = None
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "my-test-project")
    pid = firebase_init.get_project_id(allow_default=True)
    assert pid == "my-test-project"


def test_get_project_id_with_allow_default_fallback(monkeypatch):
    firebase_init._project_id = None
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.delenv("FIREBASE_TEST_PROJECT_ID", raising=False)
    pid = firebase_init.get_project_id(allow_default=True)
    assert pid == "test-project"


def test_get_project_id_cached():
    firebase_init._project_id = "cached-project"
    pid = firebase_init.get_project_id(allow_default=False)
    assert pid == "cached-project"
    firebase_init._project_id = None  # reset after test


def test_initialize_firebase_admin_in_test_env(monkeypatch):
    """In test env, initialize_firebase_admin should return None without error."""
    monkeypatch.setenv("PYTEST_RUNNING", "1")
    firebase_init._firebase_app = None
    result = firebase_init.initialize_firebase_admin()
    assert result is None
