"""Extended scheduler tests – _Job._perform_task and worker coverage."""
import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from app.services.scheduler import _Job, Scheduler


def _mock_erste_module(broker_mock):
    """Create a fake app.core.netbank.getReport module with ErsteNetBroker."""
    mod = ModuleType("app.core.netbank.getReport")
    mod.ErsteNetBroker = MagicMock(return_value=broker_mock)
    return mod


# ── _Job._perform_task ─────────────────────────────────────────────────────


def test_perform_task_import_failure(tmp_path):
    """If ErsteNetBroker import fails, _perform_task should return gracefully."""
    job = _Job("u1", tmp_path)
    # Make the import fail by injecting None for the module
    with patch.dict("sys.modules", {"app.core.netbank.getReport": None}):
        # Should not raise; logs exception and returns
        try:
            job._perform_task()
        except Exception:
            pytest.fail("_perform_task raised unexpectedly on import failure")


def test_perform_task_broker_raises(tmp_path):
    """If broker.get_report() raises, _perform_task should handle it."""
    job = _Job("u1", tmp_path)

    mock_broker = MagicMock()
    mock_broker.get_report.side_effect = RuntimeError("Selenium error")

    mock_firebase = MagicMock()
    mock_firebase.set_active_user.return_value = None

    fake_mod = _mock_erste_module(mock_broker)

    with (
        patch("app.services.login_service.firebase", mock_firebase),
        patch.dict("sys.modules", {"app.core.netbank.getReport": fake_mod}),
    ):
        # Should not raise
        job._perform_task()


def test_perform_task_creates_user_dir(tmp_path):
    """_perform_task should create user_dir if it doesn't exist."""
    user_dir = tmp_path / "newdir"
    job = _Job("u1", user_dir)

    mock_broker = MagicMock()
    mock_broker.get_report.return_value = None
    mock_firebase = MagicMock()

    fake_mod = _mock_erste_module(mock_broker)

    with (
        patch("app.services.login_service.firebase", mock_firebase),
        patch.dict("sys.modules", {"app.core.netbank.getReport": fake_mod}),
    ):
        job._perform_task()
    assert user_dir.exists()


def test_perform_task_get_report_returns_file(tmp_path):
    """_perform_task logs file info when get_report returns a filename."""
    user_dir = tmp_path / "u1"
    user_dir.mkdir()
    result_file = user_dir / "report.pkl"
    result_file.write_bytes(b"data")

    job = _Job("u1", user_dir)

    mock_broker = MagicMock()
    mock_broker.get_report.return_value = "report.pkl"
    mock_firebase = MagicMock()

    fake_mod = _mock_erste_module(mock_broker)

    with (
        patch("app.services.login_service.firebase", mock_firebase),
        patch.dict("sys.modules", {"app.core.netbank.getReport": fake_mod}),
    ):
        job._perform_task()

    mock_broker.get_report.assert_called_once()


def test_perform_task_firebase_token_load_fallback(tmp_path):
    """If set_active_user raises, falls back to load_tokens_from_dir."""
    job = _Job("u1", tmp_path)

    mock_firebase = MagicMock()
    # First call raises ValueError, second call succeeds
    mock_firebase.set_active_user.side_effect = [ValueError("no token"), None]
    mock_firebase.load_tokens_from_dir = MagicMock()

    mock_broker = MagicMock()
    mock_broker.get_report.return_value = None

    fake_mod = _mock_erste_module(mock_broker)

    with (
        patch("app.services.login_service.firebase", mock_firebase),
        patch.dict("sys.modules", {"app.core.netbank.getReport": fake_mod}),
    ):
        job._perform_task()

    mock_firebase.load_tokens_from_dir.assert_called_once()


# ── Scheduler._spawn_job_thread ────────────────────────────────────────────


def test_spawn_job_thread_starts_thread(tmp_path):
    """_spawn_job_thread should actually start a daemon thread."""
    sched = Scheduler()
    sched._start_worker_if_needed = MagicMock()

    job = _Job("u1", tmp_path)
    job._perform_task = MagicMock()  # don't actually run the task

    # _spawn_job_thread starts a thread; we just check it doesn't raise
    sched._spawn_job_thread(job)
    # Give thread a moment to start
    import time

    time.sleep(0.05)
    job._perform_task.assert_called_once()
    sched.stop_all()


# ── Scheduler.stop_all covers job stopping ────────────────────────────────


def test_stop_all_stops_running_jobs(tmp_path):
    sched = Scheduler()
    sched._start_worker_if_needed = MagicMock()

    for uid in ["a", "b"]:
        from app.services.scheduler import _Job

        j = _Job(uid, tmp_path / uid)
        sched._jobs[uid] = j

    sched.stop_all()
    assert sched._jobs == {}
    assert sched._running is False

