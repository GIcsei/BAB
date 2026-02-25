"""Tests to cover specific remaining lines in QueryHandler and scheduler."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import app.core.firestore_handler.QueryHandler as qh_mod
import pytest
from app.core.firestore_handler.QueryHandler import initialize_app


@pytest.fixture(autouse=True)
def restore_singleton():
    original = qh_mod._DEFAULT_FIREBASE
    yield
    qh_mod._DEFAULT_FIREBASE = original


def _make_fb():
    fb = initialize_app({"projectId": "p"})
    fb.api_key = "test-key"
    return fb


# ── clear_token – unlink fails (lines 187-188) ────────────────────────────


def test_clear_token_unlink_fails(tmp_path):
    """clear_token handles exception from TOKEN_FILE.unlink()."""
    fb = _make_fb()

    # Use a MagicMock Path that has exists()->True but unlink raises
    mock_path = MagicMock(spec=Path)
    mock_path.exists.return_value = True
    mock_path.unlink.side_effect = PermissionError("denied")
    fb.TOKEN_FILE = mock_path

    # should not raise
    fb.clear_token()


# ── load_tokens_from_dir – refresh write fails (lines 240-241) ────────────


def test_load_tokens_refresh_write_fails(tmp_path):
    """load_tokens_from_dir handles persistence failure after refreshing token."""
    fb = _make_fb()

    user_dir = tmp_path / "u1"
    user_dir.mkdir()
    stored = {"idToken": "old", "refreshToken": "ref", "userId": "u1"}
    cred_path = user_dir / "credentials.json"
    cred_path.write_text(json.dumps(stored))

    mock_auth_client = MagicMock()
    mock_auth_client.refresh.return_value = {
        "idToken": "new",
        "refreshToken": "new_ref",
        "userId": "u1",
    }
    fb.token_service._auth_client = mock_auth_client

    # Make persistence write fail
    with patch.object(
        fb.token_service._persistence, "write_json", side_effect=OSError("no space")
    ):
        fb.load_tokens_from_dir(tmp_path, refresh=True)

    # Token was still registered even though write failed
    assert fb.get_user_token("u1") is not None


# ── refresh_token – persistence write fails (lines 273-274) ──────────────


def test_refresh_token_persistence_write_fails_with_user_dir(tmp_path, monkeypatch):
    """refresh_token handles write failure when parent dir exists."""
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))
    fb = _make_fb()
    fb.token_service._registry.register("u1", {"idToken": "old", "refreshToken": "ref"})

    mock_auth_client = MagicMock()
    mock_auth_client.refresh.return_value = {
        "idToken": "new",
        "refreshToken": "new_ref",
        "userId": "u1",
    }
    fb.token_service._auth_client = mock_auth_client

    # Create the user directory so cred_path.parent.exists() is True
    (tmp_path / "u1").mkdir()

    with patch.object(
        fb.token_service._persistence, "write_json", side_effect=OSError("disk full")
    ):
        result = fb.refresh_token("u1")

    # Token was refreshed in memory despite persistence failure
    assert result["idToken"] == "new"


# ── scheduler – start_job chmod fails in start_job_for_user (lines 278-279)


def test_start_job_chmod_fails(tmp_path):
    """start_job_for_user handles chmod failure after mkdir succeeds."""
    from app.services.scheduler import Scheduler

    sched = Scheduler()
    sched._start_worker_if_needed = MagicMock()

    with patch(
        "app.infrastructure.sched.scheduler.os.chmod",
        side_effect=OSError("not supported"),
    ):
        job = sched.start_job_for_user("u1", tmp_path / "u1", 18, 0)

    assert job is not None
    assert "u1" in sched._jobs
    sched.stop_all()


# ── scheduler – stop_all job stopping exception (lines 341-342) ───────────


def test_stop_all_job_stopping_exception(tmp_path):
    """stop_all handles exception when marking jobs stopped."""
    from app.services.scheduler import Scheduler, _Job

    sched = Scheduler()
    sched._start_worker_if_needed = MagicMock()

    # Create a mock job where setting _stopped raises
    mock_job = MagicMock(spec=_Job)
    type(mock_job)._stopped = property(
        fget=lambda s: False,
        fset=lambda s, v: (_ for _ in ()).throw(AttributeError("frozen")),
    )
    sched._jobs["u1"] = mock_job

    # stop_all should not raise even with bad jobs
    sched.stop_all()
    assert sched._jobs == {}
    assert sched._running is False


# ── scheduler – trigger_run one-off failure (lines 409-411) ──────────────


def test_trigger_run_onoff_failure_returns_false(tmp_path, monkeypatch):
    """trigger_run_for_user returns False when one-off spawn fails."""
    from app.services.scheduler import Scheduler

    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))

    sched = Scheduler()
    sched._start_worker_if_needed = MagicMock()

    # No existing job for this user -> will take one-off path
    assert "new_user" not in sched._jobs

    with patch.object(sched, "_spawn_job_thread", side_effect=RuntimeError("fail")):
        result = sched.trigger_run_for_user("new_user")

    assert result is False
    sched.stop_all()
