"""Tests to cover remaining scheduler branches and worker loop."""

import heapq
import time
from unittest.mock import MagicMock, patch

import pytest
from app.services.scheduler import Scheduler, _Job

# ── _start_worker_if_needed (lines 171-179) ────────────────────────────────


def test_start_worker_if_needed_starts_thread(tmp_path):
    """_start_worker_if_needed should start a worker thread when not running."""
    sched = Scheduler()

    with patch.object(sched, "_spawn_job_thread"):
        sched._start_worker_if_needed()
        assert sched._running is True
        assert sched._worker is not None
        assert sched._worker.is_alive()

    sched.stop_all()


def test_start_worker_if_needed_already_running(tmp_path):
    """If already running, _start_worker_if_needed notifies instead of starting new thread."""
    sched = Scheduler()

    with patch.object(sched, "_spawn_job_thread"):
        sched._start_worker_if_needed()  # starts worker
        first_worker = sched._worker
        sched._start_worker_if_needed()  # should not start new thread
        assert sched._worker is first_worker

    sched.stop_all()


# ── Worker loop integration test (lines 186-245) ──────────────────────────


def test_worker_loop_fires_job_immediately(tmp_path):
    """Worker loop should fire a job whose scheduled time is in the past."""
    sched = Scheduler()
    job = _Job("u1", tmp_path, target_hour=18, target_minute=0)
    job._perform_task = MagicMock()

    # Inject job directly into scheduler
    with sched._lock:
        sched._jobs["u1"] = job
        sched._counter += 1
        # Push with past timestamp so it fires immediately
        heapq.heappush(sched._heap, (time.time() - 10, sched._counter, "u1"))

    with patch.object(
        sched, "_spawn_job_thread", wraps=sched._spawn_job_thread
    ) as mock_spawn:
        sched._start_worker_if_needed()
        # Give worker time to fire the job
        time.sleep(0.3)

    sched.stop_all()
    mock_spawn.assert_called()


def test_worker_loop_skips_removed_job(tmp_path):
    """Worker loop should skip jobs that were removed from _jobs dict."""
    sched = Scheduler()

    # Push a past-timestamp job for a user that doesn't exist in _jobs
    with sched._lock:
        sched._counter += 1
        heapq.heappush(sched._heap, (time.time() - 10, sched._counter, "removed_user"))

    with patch.object(sched, "_spawn_job_thread") as mock_spawn:
        sched._start_worker_if_needed()
        time.sleep(0.2)

    sched.stop_all()
    mock_spawn.assert_not_called()


def test_worker_loop_stops_when_running_false(tmp_path):
    """Worker loop should exit when _running is set to False."""
    sched = Scheduler()
    sched._start_worker_if_needed()
    assert sched._running is True

    sched.stop_all()
    assert sched._running is False


# ── start_job_for_user – mkdir failure (lines 278-282) ────────────────────


def test_start_job_mkdir_failure(tmp_path):
    """start_job_for_user should propagate exception if mkdir fails."""
    sched = Scheduler()
    sched._start_worker_if_needed = MagicMock()

    with patch(
        "app.infrastructure.sched.scheduler.Path.mkdir",
        side_effect=PermissionError("denied"),
    ):
        with pytest.raises(PermissionError):
            sched.start_job_for_user("u1", tmp_path / "u1", 18, 0)


# ── start_job_for_user – old job marking exception (lines 290-291) ────────


def test_start_job_restart_marking_stopped_exception(tmp_path):
    """start_job_for_user should handle exception when marking old job stopped."""
    sched = Scheduler()
    sched._is_leader = True
    sched._start_worker_if_needed = MagicMock()

    # Create old job with a property that raises on attribute set
    old_job = MagicMock(spec=_Job)
    type(old_job)._stopped = property(
        fget=lambda s: False,
        fset=lambda s, v: (_ for _ in ()).throw(RuntimeError("can't stop")),
    )
    sched._jobs["u1"] = old_job

    user_dir = tmp_path / "u1"
    # Should not raise even if marking old job fails
    new_job = sched.start_job_for_user("u1", user_dir, 18, 0)
    assert new_job is not None


# ── get_next_run_for_user – exception handling (lines 317-319) ────────────


def test_get_next_run_exception_returns_none(tmp_path):
    """get_next_run_for_user should return None if _seconds_until_next_target raises."""
    sched = Scheduler()
    sched._is_leader = True
    sched._start_worker_if_needed = MagicMock()

    user_dir = tmp_path / "u1"
    sched.start_job_for_user("u1", user_dir, 18, 0)
    job = sched._jobs["u1"]

    with patch.object(
        job, "_seconds_until_next_target", side_effect=RuntimeError("oops")
    ):
        result = sched.get_next_run_for_user("u1")

    assert result is None
    sched.stop_all()


# ── stop_job_for_user – stopping exception (lines 329-330) ────────────────


def test_stop_job_stopping_exception(tmp_path):
    """stop_job_for_user should handle exception when job._stopped raises."""
    sched = Scheduler()
    sched._start_worker_if_needed = MagicMock()

    # Create a job-like object where setting _stopped raises
    mock_job = MagicMock(spec=_Job)
    type(mock_job)._stopped = property(
        fget=lambda s: False,
        fset=lambda s, v: (_ for _ in ()).throw(RuntimeError("immutable")),
    )
    sched._jobs["u1"] = mock_job

    result = sched.stop_job_for_user("u1")
    assert result is True  # returned True despite the exception


# ── stop_all – joining worker thread (line 348) ────────────────────────────


def test_stop_all_joins_worker_thread(tmp_path):
    """stop_all should join the worker thread if it's alive."""
    sched = Scheduler()
    sched._start_worker_if_needed()  # starts actual worker thread
    assert sched._worker is not None
    assert sched._worker.is_alive()

    sched.stop_all()
    # After stop_all, worker should have stopped
    assert sched._running is False


# ── restore_jobs_from_dir – non-dir entry (lines 364-365) ─────────────────


def test_restore_jobs_skips_files(tmp_path):
    """restore_jobs_from_dir should skip regular files."""
    sched = Scheduler()
    sched._is_leader = True
    sched._start_worker_if_needed = MagicMock()

    # Create a file (not a directory) in base_dir
    (tmp_path / "notadir.txt").write_text("data")
    # Create a user dir with credentials.json
    user_dir = tmp_path / "real_user"
    user_dir.mkdir()
    (user_dir / "credentials.json").write_text('{"idToken": "t"}')

    sched.restore_jobs_from_dir(tmp_path)
    assert "real_user" in sched._jobs
    assert "notadir.txt" not in sched._jobs
    sched.stop_all()


# ── restore_jobs_from_dir – start_job_for_user exception (lines 374-375) ──


def test_restore_jobs_handles_start_failure(tmp_path):
    """restore_jobs_from_dir should continue if one job fails to start."""
    sched = Scheduler()
    sched._is_leader = True
    sched._start_worker_if_needed = MagicMock()

    # Two user dirs with credentials
    for uid in ["ok_user", "fail_user"]:
        d = tmp_path / uid
        d.mkdir()
        (d / "credentials.json").write_text('{"idToken": "t"}')

    call_count = [0]

    original_start = sched.start_job_for_user

    def patched_start(user_id, *args, **kwargs):
        call_count[0] += 1
        if user_id == "fail_user":
            raise RuntimeError("job start failed")
        return original_start(user_id, *args, **kwargs)

    sched.start_job_for_user = patched_start

    # Should not raise even if one job fails
    sched.restore_jobs_from_dir(tmp_path)
    assert call_count[0] == 2
    sched.stop_all()
