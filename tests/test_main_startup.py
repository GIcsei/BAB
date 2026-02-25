"""Tests for app.main – startup event in test mode and non-test mode."""

import os

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

from unittest.mock import MagicMock, patch

import pytest

from app.core.health import HealthStatus
from app.main import startup_event


@pytest.fixture()
def fresh_health():
    """Provide a fresh HealthStatus instance."""
    h = HealthStatus()
    return h


# ── startup_event – test environment (short path) ─────────────────────────


def test_startup_test_env_marks_components_ready(monkeypatch):
    """In test mode, startup marks all components as skipped (ready=False)."""
    monkeypatch.setenv("PYTEST_RUNNING", "1")
    h = HealthStatus()

    with patch("app.main.get_health", return_value=h):
        import asyncio

        asyncio.get_event_loop().run_until_complete(startup_event())

    # In test mode, components are marked with "skipped_in_tests" error
    assert h.components["scheduler"]["error"] == "skipped_in_tests"
    assert h.components["tokens"]["error"] == "skipped_in_tests"
    assert h.components["firebase"]["error"] == "skipped_in_tests"
    assert h.is_ready is True


# ── startup_event – non-test environment (full path with mocks) ────────────


def test_startup_full_path_with_mocks(tmp_path, monkeypatch):
    """Test non-test startup path with mocked scheduler and firebase."""
    # Remove test env vars
    monkeypatch.delenv("PYTEST_RUNNING", raising=False)
    monkeypatch.delenv("UNIT_TEST", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APP_JOB_HOUR", "10")
    monkeypatch.setenv("APP_JOB_MINUTE", "30")

    h = HealthStatus()
    mock_scheduler = MagicMock()
    mock_scheduler.restore_jobs_from_dir = MagicMock()

    mock_firebase = MagicMock()
    mock_firebase.load_tokens_from_dir = MagicMock()

    with (
        patch("app.main.get_health", return_value=h),
        patch("app.main.is_testing_env", return_value=False),
        patch("app.main.scheduler", mock_scheduler),
        patch("app.main.get_firebase", return_value=mock_firebase),
    ):
        import asyncio

        asyncio.get_event_loop().run_until_complete(startup_event())

    assert h.is_ready is True
    mock_scheduler.restore_jobs_from_dir.assert_called_once()
    mock_firebase.load_tokens_from_dir.assert_called_once()


def test_startup_scheduler_none(tmp_path, monkeypatch):
    """Startup should still succeed when scheduler is None (lock not acquired)."""
    monkeypatch.delenv("PYTEST_RUNNING", raising=False)
    monkeypatch.delenv("UNIT_TEST", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))

    h = HealthStatus()
    mock_firebase = MagicMock()
    mock_firebase.load_tokens_from_dir = MagicMock()

    with (
        patch("app.main.get_health", return_value=h),
        patch("app.main.is_testing_env", return_value=False),
        patch("app.main.scheduler", None),
        patch("app.main.get_firebase", return_value=mock_firebase),
    ):
        import asyncio

        asyncio.get_event_loop().run_until_complete(startup_event())

    assert h.is_ready is True


def test_startup_token_load_failure_raises(tmp_path, monkeypatch):
    """If load_tokens_from_dir raises, startup should propagate the exception."""
    monkeypatch.delenv("PYTEST_RUNNING", raising=False)
    monkeypatch.delenv("UNIT_TEST", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))

    h = HealthStatus()
    mock_scheduler = MagicMock()
    mock_firebase = MagicMock()
    mock_firebase.load_tokens_from_dir.side_effect = RuntimeError("DB unavailable")

    with (
        patch("app.main.get_health", return_value=h),
        patch("app.main.is_testing_env", return_value=False),
        patch("app.main.scheduler", mock_scheduler),
        patch("app.main.get_firebase", return_value=mock_firebase),
    ):
        import asyncio

        with pytest.raises(RuntimeError, match="DB unavailable"):
            asyncio.get_event_loop().run_until_complete(startup_event())
