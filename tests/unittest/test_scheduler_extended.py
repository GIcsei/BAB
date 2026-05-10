import threading
import time
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


def test_spawn_job_thread_skips_duplicate_while_inflight(tmp_path):
    sched = Scheduler(firebase_provider=lambda: MagicMock())

    started = threading.Event()
    release = threading.Event()
    run_count = [0]

    def blocking_task():
        run_count[0] += 1
        started.set()
        release.wait(timeout=1.0)

    job = _Job("u1", tmp_path, firebase_provider=lambda: MagicMock())
    job._perform_task = blocking_task

    assert sched._spawn_job_thread(job) is True
    assert started.wait(timeout=0.5)
    assert sched._spawn_job_thread(job) is True
    time.sleep(0.05)
    assert run_count[0] == 1

    release.set()
    time.sleep(0.1)

    assert sched._spawn_job_thread(job) is True
    time.sleep(0.1)
    assert run_count[0] == 2
    sched.stop_all()


def test_trigger_run_for_user_duplicate_while_inflight_is_noop(tmp_path):
    sched = Scheduler(firebase_provider=lambda: MagicMock())

    started = threading.Event()
    release = threading.Event()
    run_count = [0]

    def blocking_task():
        run_count[0] += 1
        started.set()
        release.wait(timeout=1.0)

    job = _Job("u1", tmp_path / "u1", firebase_provider=lambda: MagicMock())
    job._perform_task = blocking_task
    sched._jobs["u1"] = job

    assert sched.trigger_run_for_user("u1") is True
    assert started.wait(timeout=0.5)
    assert sched.trigger_run_for_user("u1") is True
    time.sleep(0.05)
    assert run_count[0] == 1

    release.set()
    time.sleep(0.1)

    assert sched.trigger_run_for_user("u1") is True
    time.sleep(0.1)
    assert run_count[0] == 2
    sched.stop_all()


def test_stop_all_stops_running_jobs(tmp_path):
    sched = Scheduler(firebase_provider=lambda: MagicMock())

    for uid in ["a", "b"]:
        j = _Job(uid, tmp_path / uid, firebase_provider=lambda: MagicMock())
        sched._jobs[uid] = j

    sched.stop_all()
    assert sched._jobs == {}
    assert sched._running is False


def test_start_bootstraps_leadership_before_monitor_loop(tmp_path):
    sched = Scheduler(
        firebase_provider=lambda: MagicMock(),
        base_dir=tmp_path,
        target_hour=7,
        target_minute=45,
    )

    with (
        patch.object(sched, "_try_acquire_leadership", return_value=True) as acquire,
        patch.object(sched, "_on_became_leader") as became,
        patch.object(sched, "_reconcile_jobs_from_dir") as reconcile,
    ):
        sched.start()
        sched.stop_all()

    assert acquire.call_count >= 1
    assert became.call_count >= 1
    reconcile.assert_any_call(tmp_path, 7, 45)


def test_try_acquire_leadership_non_fcntl_defaults_to_follower(monkeypatch, tmp_path):
    sched = Scheduler(base_dir=tmp_path, acquire_lock=True)
    monkeypatch.delenv("APP_SCHEDULER_NO_FCNTL_ASSUME_LEADER", raising=False)

    with patch("app.infrastructure.sched.scheduler.fcntl", None):
        assert sched._try_acquire_leadership() is False
        assert sched.is_leader() is False


def test_try_acquire_leadership_non_fcntl_env_opt_in(monkeypatch, tmp_path):
    sched = Scheduler(base_dir=tmp_path, acquire_lock=True)
    monkeypatch.setenv("APP_SCHEDULER_NO_FCNTL_ASSUME_LEADER", "true")

    with patch("app.infrastructure.sched.scheduler.fcntl", None):
        assert sched._try_acquire_leadership() is True
        assert sched.is_leader() is True
