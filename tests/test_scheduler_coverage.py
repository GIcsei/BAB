"""Tests for scheduler worker loop edge cases."""

import heapq
import time
from types import ModuleType
from unittest.mock import MagicMock, patch

from app.services.scheduler import Scheduler, _Job


def _mock_erste_module(broker_mock):
    mod = ModuleType("app.core.netbank.getReport")
    mod.ErsteNetBroker = MagicMock(return_value=broker_mock)
    return mod


# ── Worker loop – stopped job is skipped (lines 221-225) ──────────────────


def test_worker_skips_stopped_job(tmp_path):
    """Worker loop should skip a job that is marked as _stopped."""
    sched = Scheduler()

    job = _Job("u1", tmp_path)
    job._stopped = True  # pre-stop it
    job._perform_task = MagicMock()

    with sched._lock:
        sched._jobs["u1"] = job
        sched._counter += 1
        heapq.heappush(sched._heap, (time.time() - 10, sched._counter, "u1"))

    with patch.object(sched, "_spawn_job_thread") as mock_spawn:
        sched._start_worker_if_needed()
        time.sleep(0.3)

    sched.stop_all()
    mock_spawn.assert_not_called()


# ── Worker loop – spawn raises (lines 228-229) ────────────────────────────


def test_worker_handles_spawn_failure(tmp_path):
    """Worker loop should continue if _spawn_job_thread raises."""
    sched = Scheduler()

    job = _Job("u1", tmp_path)
    job._perform_task = MagicMock()

    with sched._lock:
        sched._jobs["u1"] = job
        sched._counter += 1
        heapq.heappush(sched._heap, (time.time() - 10, sched._counter, "u1"))

    spawn_calls = [0]

    def raising_spawn(j):
        spawn_calls[0] += 1
        raise RuntimeError("spawn failed")

    sched._spawn_job_thread = raising_spawn
    sched._start_worker_if_needed()
    time.sleep(0.3)
    sched.stop_all()

    # spawn was attempted despite failure
    assert spawn_calls[0] >= 1


# ── Worker loop – job reschedule (lines 233-244) ──────────────────────────


def test_worker_reschedules_job_after_run(tmp_path):
    """Worker loop should reschedule job after it runs."""
    sched = Scheduler()

    job = _Job("u1", tmp_path)
    job._perform_task = MagicMock()  # fast mock

    with sched._lock:
        sched._jobs["u1"] = job
        sched._counter += 1
        heapq.heappush(sched._heap, (time.time() - 10, sched._counter, "u1"))

    spawned_count = [0]

    def counting_spawn(j):
        spawned_count[0] += 1
        # Run in a thread so it's fast
        import threading

        t = threading.Thread(target=j._perform_task, daemon=True)
        t.start()

    sched._spawn_job_thread = counting_spawn
    sched._start_worker_if_needed()
    time.sleep(0.3)

    sched.stop_all()
    assert spawned_count[0] >= 1


# ── _perform_task – mkdir failure (lines 82-84) ───────────────────────────


def test_perform_task_mkdir_failure(tmp_path):
    """_perform_task should return gracefully if mkdir fails."""
    job = _Job("u1", tmp_path / "newdir")

    with patch(
        "app.infrastructure.sched.scheduler.Path.mkdir",
        side_effect=OSError("permission denied"),
    ):
        # should not raise
        job._perform_task()


# ── _perform_task – chmod failure (lines 79-81) ──────────────────────────


def test_perform_task_chmod_failure(tmp_path):
    """_perform_task should handle chmod failure without raising."""
    mock_broker = MagicMock()
    mock_broker.get_report.return_value = None
    mock_firebase = MagicMock()

    fake_mod = _mock_erste_module(mock_broker)

    with (
        patch.dict("sys.modules", {"app.core.netbank.getReport": fake_mod}),
        patch("os.chmod", side_effect=OSError("not supported")),
    ):
        job = _Job("u1", tmp_path)
        job._firebase_provider = lambda: mock_firebase
        job._perform_task()  # should not raise


# ── _perform_task – firebase import failure (lines 115-121) ──────────────


def test_perform_task_firebase_all_methods_fail(tmp_path):
    """_perform_task handles case where all firebase methods fail."""
    mock_broker = MagicMock()
    mock_broker.get_report.return_value = None

    fake_mod = _mock_erste_module(mock_broker)

    mock_firebase = MagicMock()
    # All firebase methods raise
    mock_firebase.set_active_user.side_effect = RuntimeError("set_active fails")
    mock_firebase.load_tokens_from_dir.side_effect = RuntimeError("load fails")

    with (patch.dict("sys.modules", {"app.core.netbank.getReport": fake_mod}),):
        job = _Job("u1", tmp_path)
        job._firebase_provider = lambda: mock_firebase
        job._perform_task()  # should not raise

    mock_broker.get_report.assert_called_once()


# ── _perform_task – result file stat failure (lines 138-139) ──────────────


def test_perform_task_result_file_stat_fails(tmp_path):
    """_perform_task handles file stat failure gracefully."""
    mock_broker = MagicMock()
    # Return a filename that doesn't exist
    mock_broker.get_report.return_value = "nonexistent.pkl"
    mock_firebase = MagicMock()

    fake_mod = _mock_erste_module(mock_broker)

    with (patch.dict("sys.modules", {"app.core.netbank.getReport": fake_mod}),):
        job = _Job("u1", tmp_path)
        job._firebase_provider = lambda: mock_firebase
        # file doesn't exist so stat will fail -> size = None
        job._perform_task()

    mock_broker.get_report.assert_called_once()
