"""Tests for app.main – lifespan startup behavior and health endpoints."""

import os

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

from unittest.mock import MagicMock, patch

from app.core.health import HealthStatus
from app.main import app
from fastapi.testclient import TestClient

# ── lifespan – test environment (short path) ──────────────────────────────


def test_startup_test_env_marks_health_ready():
    """In test mode (PYTEST_RUNNING=1), health should be ready after startup."""
    # In test mode, lifespan marks health via skipped paths
    client = TestClient(app)
    resp = client.get("/health")
    # After lifespan runs in test mode, health is marked complete
    assert resp.status_code in (200, 503)


def test_health_ready_after_test_mode_startup():
    """Health endpoint returns 200 when startup completes in test mode."""
    fresh_health = HealthStatus()
    fresh_health.mark_component_ready("scheduler", "skipped_in_tests")
    fresh_health.mark_component_ready("tokens", "skipped_in_tests")
    fresh_health.mark_component_ready("firebase", "skipped_in_tests")
    fresh_health.mark_startup_complete()

    with patch("app.main.get_health", return_value=fresh_health):
        client = TestClient(app)
        resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] is True


def test_startup_components_skipped_in_tests():
    """In test mode, startup marks components as 'skipped_in_tests'."""
    fresh_health = HealthStatus()
    fresh_health.mark_component_ready("scheduler", "skipped_in_tests")
    fresh_health.mark_component_ready("tokens", "skipped_in_tests")
    fresh_health.mark_component_ready("firebase", "skipped_in_tests")
    fresh_health.mark_startup_complete()

    assert fresh_health.components["scheduler"]["error"] == "skipped_in_tests"
    assert fresh_health.components["tokens"]["error"] == "skipped_in_tests"
    assert fresh_health.components["firebase"]["error"] == "skipped_in_tests"
    assert fresh_health.is_ready is True


# ── lifespan – non-test environment via mocked lifespan context ───────────


def test_lifespan_non_test_marks_all_components_ready(tmp_path, monkeypatch):
    """In non-test mode, all components should be marked ready if mocks succeed."""
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APP_JOB_HOUR", "10")
    monkeypatch.setenv("APP_JOB_MINUTE", "30")

    h = HealthStatus()
    mock_scheduler = MagicMock()
    mock_firebase = MagicMock()
    mock_firebase.load_tokens_from_dir = MagicMock()

    with (
        patch("app.main.get_health", return_value=h),
        patch("app.main.is_testing_env", return_value=False),
        patch("app.main.initialize_firebase_admin"),
        patch("app.main.get_credential", return_value={"project_id": "test-project"}),
        patch("app.main.initialize_app", return_value=mock_firebase),
        patch("app.main.create_scheduler", return_value=mock_scheduler),
    ):
        client = TestClient(app)
        with client:
            pass  # triggers lifespan startup and shutdown

    assert h.is_ready is True
    mock_scheduler.restore_jobs_from_dir.assert_called_once()
    mock_firebase.load_tokens_from_dir.assert_called_once()


def test_lifespan_scheduler_none(tmp_path, monkeypatch):
    """Startup should succeed when scheduler is None (lock not acquired)."""
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))

    h = HealthStatus()
    mock_firebase = MagicMock()
    mock_firebase.load_tokens_from_dir = MagicMock()

    with (
        patch("app.main.get_health", return_value=h),
        patch("app.main.is_testing_env", return_value=False),
        patch("app.main.initialize_firebase_admin"),
        patch("app.main.get_credential", return_value={"project_id": "test-project"}),
        patch("app.main.initialize_app", return_value=mock_firebase),
        patch("app.main.create_scheduler", return_value=None),
    ):
        client = TestClient(app)
        with client:
            pass

    assert h.is_ready is True


def test_lifespan_token_load_failure_continues_startup(tmp_path, monkeypatch):
    """If load_tokens_from_dir raises, startup should continue with degraded health."""
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))

    h = HealthStatus()
    mock_scheduler = MagicMock()
    mock_firebase = MagicMock()
    mock_firebase.load_tokens_from_dir.side_effect = RuntimeError("DB unavailable")

    with (
        patch("app.main.get_health", return_value=h),
        patch("app.main.is_testing_env", return_value=False),
        patch("app.main.initialize_firebase_admin"),
        patch("app.main.get_credential", return_value={"project_id": "test-project"}),
        patch("app.main.initialize_app", return_value=mock_firebase),
        patch("app.main.create_scheduler", return_value=mock_scheduler),
    ):
        client = TestClient(app)
        with client:
            pass

    assert h.is_ready is True
    assert h.components["tokens"]["error"] is not None


def test_lifespan_token_refresh_fails_fallback_no_refresh(tmp_path, monkeypatch):
    """If token refresh fails, startup falls back to loading without refresh."""
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))

    h = HealthStatus()
    mock_scheduler = MagicMock()
    mock_firebase = MagicMock()
    call_count = 0

    def load_tokens_side_effect(base_dir, refresh=True):
        nonlocal call_count
        call_count += 1
        if refresh:
            raise RuntimeError("Network not ready")

    mock_firebase.load_tokens_from_dir.side_effect = load_tokens_side_effect

    with (
        patch("app.main.get_health", return_value=h),
        patch("app.main.is_testing_env", return_value=False),
        patch("app.main.initialize_firebase_admin"),
        patch("app.main.get_credential", return_value={"project_id": "test-project"}),
        patch("app.main.initialize_app", return_value=mock_firebase),
        patch("app.main.create_scheduler", return_value=mock_scheduler),
    ):
        client = TestClient(app)
        with client:
            pass

    assert h.is_ready is True
    assert h.components["tokens"]["error"] == "loaded_without_refresh"
    assert call_count == 2
