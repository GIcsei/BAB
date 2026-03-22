"""Tests for app.services.scheduler – _Job and Scheduler."""

import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from app.services.scheduler import Scheduler, _Job

# ── _Job ───────────────────────────────────────────────────────────────────


def test_job_seconds_until_next_target_positive(tmp_path):
    # target far in the future -> should be positive
    job = _Job("u1", tmp_path, target_hour=23, target_minute=59)
    secs = job._seconds_until_next_target()
    assert secs >= 0


def test_job_seconds_until_next_target_past_gives_next_day(tmp_path):
    """When target time has already passed today, next run is tomorrow."""
    job = _Job("u1", tmp_path, target_hour=0, target_minute=0)
    secs = job._seconds_until_next_target()
    # Can be 0 at midnight exactly, otherwise positive
    assert secs >= 0
    assert secs <= 86400 + 1  # no more than one day


def test_job_next_run_epoch_ms(tmp_path):
    job = _Job("u1", tmp_path)
    ms = job.next_run_epoch_ms()
    assert isinstance(ms, int)
    assert ms > time.time() * 1000 - 100  # not in the past


def test_job_compute_next_run_dt(tmp_path):
    job = _Job("u1", tmp_path, target_hour=12, target_minute=0)
    dt = job.compute_next_run_dt()
    assert isinstance(dt, datetime)
    assert dt > datetime.now()


def test_job_defaults(tmp_path):
    job = _Job("alice", tmp_path)
    assert job.user_id == "alice"
    assert job.target_hour == 18
    assert job.target_minute == 0
    assert job._stopped is False


def test_job_stopped_flag(tmp_path):
    job = _Job("u2", tmp_path)
    job._stopped = True
    assert job._stopped is True


# ── Scheduler ─────────────────────────────────────────────────────────────


@pytest.fixture
def sched(tmp_path):
    """Fresh scheduler instance without starting the worker thread."""
    s = Scheduler()
    s._is_leader = True  # tests don't use leadership locking
    # Patch _start_worker_if_needed to prevent thread start in tests
    s._start_worker_if_needed = MagicMock()
    yield s
    s.stop_all()


def test_start_job_for_user(sched, tmp_path):
    user_dir = tmp_path / "u1"
    job = sched.start_job_for_user("u1", user_dir, 18, 0)
    assert job is not None
    assert "u1" in sched._jobs


def test_start_job_creates_user_dir(sched, tmp_path):
    user_dir = tmp_path / "newuser"
    assert not user_dir.exists()
    sched.start_job_for_user("newuser", user_dir, 18, 0)
    assert user_dir.exists()


def test_start_job_no_duplicate_for_active_user(sched, tmp_path):
    user_dir = tmp_path / "u1"
    job1 = sched.start_job_for_user("u1", user_dir, 18, 0)
    job2 = sched.start_job_for_user("u1", user_dir, 18, 0)
    # Active job must not be replaced; same object returned
    assert job1 is job2
    assert not job1._stopped
    assert sched._jobs["u1"] is job1


def test_start_job_replaces_stopped_job(sched, tmp_path):
    user_dir = tmp_path / "u1"
    job1 = sched.start_job_for_user("u1", user_dir, 18, 0)
    job1._stopped = True
    job2 = sched.start_job_for_user("u1", user_dir, 18, 0)
    # Stopped job should be replaced with a fresh one
    assert job1 is not job2
    assert not job2._stopped
    assert sched._jobs["u1"] is job2


def test_get_next_run_for_user_no_job(sched):
    result = sched.get_next_run_for_user("nobody")
    assert result is None


def test_get_next_run_for_user_with_job(sched, tmp_path):
    user_dir = tmp_path / "u1"
    sched.start_job_for_user("u1", user_dir, 18, 0)
    result = sched.get_next_run_for_user("u1")
    assert result is not None
    assert "seconds_until_next_run" in result
    assert "next_run_timestamp_ms" in result
    assert result["seconds_until_next_run"] >= 0


def test_stop_job_for_user(sched, tmp_path):
    user_dir = tmp_path / "u1"
    sched.start_job_for_user("u1", user_dir, 18, 0)
    result = sched.stop_job_for_user("u1")
    assert result is True
    assert "u1" not in sched._jobs


def test_stop_job_for_user_not_found(sched):
    result = sched.stop_job_for_user("nobody")
    assert result is False


def test_stop_all(sched, tmp_path):
    for uid in ["u1", "u2", "u3"]:
        sched.start_job_for_user(uid, tmp_path / uid, 18, 0)
    sched.stop_all()
    assert sched._jobs == {}


def test_restore_jobs_from_dir(sched, tmp_path):
    base = tmp_path / "users"
    base.mkdir()
    # create two user directories with credentials.json
    for uid in ["user_a", "user_b"]:
        d = base / uid
        d.mkdir()
        (d / "credentials.json").write_text('{"idToken": "x"}')
    # also a dir without credentials (should be skipped)
    (base / "user_c").mkdir()

    sched.restore_jobs_from_dir(base, target_hour=8, target_minute=30)
    assert "user_a" in sched._jobs
    assert "user_b" in sched._jobs
    assert "user_c" not in sched._jobs


def test_restore_jobs_from_dir_nonexistent(sched, tmp_path):
    # should not raise even if base_dir doesn't exist
    sched.restore_jobs_from_dir(tmp_path / "nonexistent")


def test_trigger_run_for_user_with_existing_job(sched, tmp_path):
    user_dir = tmp_path / "u1"
    sched.start_job_for_user("u1", user_dir, 18, 0)
    with patch.object(sched, "_spawn_job_thread") as mock_spawn:
        result = sched.trigger_run_for_user("u1")
    assert result is True
    mock_spawn.assert_called_once()


def test_trigger_run_for_user_no_job(sched, tmp_path, monkeypatch):
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))
    with patch.object(sched, "_spawn_job_thread") as mock_spawn:
        result = sched.trigger_run_for_user("new_user")
    assert result is True
    mock_spawn.assert_called_once()


def test_trigger_run_spawn_failure_returns_false(sched, tmp_path):
    user_dir = tmp_path / "u1"
    sched.start_job_for_user("u1", user_dir, 18, 0)
    with patch.object(sched, "_spawn_job_thread", side_effect=RuntimeError("fail")):
        result = sched.trigger_run_for_user("u1")
    assert result is False
