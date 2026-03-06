from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
from app.infrastructure.sched.scheduler import Scheduler, _Job


def _mock_erste_module(broker_mock):
    mod = ModuleType("app.core.netbank.getReport")
    mod.ErsteNetBroker = MagicMock(return_value=broker_mock)
    return mod


def test_perform_task_import_failure(tmp_path):
    job = _Job("u1", tmp_path, firebase_provider=lambda: None)
    with patch.dict("sys.modules", {"app.core.netbank.getReport": None}):
        try:
            job._perform_task()
        except Exception:
            pytest.fail("_perform_task raised unexpectedly on import failure")


def test_perform_task_broker_raises(tmp_path):
    mock_broker = MagicMock()
    mock_broker.get_report.side_effect = RuntimeError("Selenium error")

    mock_firebase = MagicMock()
    job = _Job("u1", tmp_path, firebase_provider=lambda: mock_firebase)

    fake_mod = _mock_erste_module(mock_broker)

    with patch.dict("sys.modules", {"app.core.netbank.getReport": fake_mod}):
        job._perform_task()


def test_perform_task_creates_user_dir(tmp_path):
    user_dir = tmp_path / "newdir"
    mock_broker = MagicMock()
    mock_broker.get_report.return_value = None
    job = _Job("u1", user_dir, firebase_provider=lambda: MagicMock())

    fake_mod = _mock_erste_module(mock_broker)

    with patch.dict("sys.modules", {"app.core.netbank.getReport": fake_mod}):
        job._perform_task()
    assert user_dir.exists()


def test_perform_task_get_report_returns_file(tmp_path):
    user_dir = tmp_path / "u1"
    user_dir.mkdir()
    result_file = user_dir / "report.pkl"
    result_file.write_bytes(b"data")

    mock_broker = MagicMock()
    mock_broker.get_report.return_value = "report.pkl"
    job = _Job("u1", user_dir, firebase_provider=lambda: MagicMock())

    fake_mod = _mock_erste_module(mock_broker)

    with patch.dict("sys.modules", {"app.core.netbank.getReport": fake_mod}):
        job._perform_task()

    mock_broker.get_report.assert_called_once()


def test_perform_task_firebase_token_load_fallback(tmp_path):
    mock_firebase = MagicMock()
    mock_firebase.set_active_user.side_effect = [ValueError("no token"), None]
    mock_firebase.load_tokens_from_dir = MagicMock()

    mock_broker = MagicMock()
    mock_broker.get_report.return_value = None
    job = _Job("u1", tmp_path, firebase_provider=lambda: mock_firebase)

    fake_mod = _mock_erste_module(mock_broker)

    with patch.dict("sys.modules", {"app.core.netbank.getReport": fake_mod}):
        job._perform_task()

    mock_firebase.load_tokens_from_dir.assert_called_once()


def test_spawn_job_thread_starts_thread(tmp_path):
    sched = Scheduler(firebase_provider=lambda: MagicMock())

    job = _Job("u1", tmp_path, firebase_provider=lambda: MagicMock())
    job._perform_task = MagicMock()

    sched._spawn_job_thread(job)
    import time

    time.sleep(0.05)
    job._perform_task.assert_called_once()
    sched.stop_all()


def test_stop_all_stops_running_jobs(tmp_path):
    sched = Scheduler(firebase_provider=lambda: MagicMock())

    for uid in ["a", "b"]:
        j = _Job(uid, tmp_path / uid, firebase_provider=lambda: MagicMock())
        sched._jobs[uid] = j

    sched.stop_all()
    assert sched._jobs == {}
    assert sched._running is False
