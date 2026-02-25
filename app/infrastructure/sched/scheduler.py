import fcntl
import heapq
import logging
import os
import threading
import time
from datetime import datetime
from datetime import time as dt_time
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_SCHED_LOCK_FD = None


class _Job:
    """
    Lightweight descriptor for a per-user scheduled job.
    The heavy task logic remains in `_perform_task` and is run in worker threads.
    """

    def __init__(
        self,
        user_id: str,
        user_dir: Path,
        target_hour: int = 18,
        target_minute: int = 0,
        firebase_provider: Optional[Callable[[], Any]] = None,
    ):
        self.user_id = user_id
        self.user_dir = Path(user_dir)
        self.target_hour = int(target_hour)
        self.target_minute = int(target_minute)
        self._stopped = False
        self._firebase_provider = firebase_provider
        self.logger = logging.getLogger(f"{__name__}.job.{user_id}")
        self.logger.debug(
            "Job.__init__ user_dir=%s target=%02d:%02d",
            str(user_dir),
            self.target_hour,
            self.target_minute,
        )

    def _seconds_until_next_target(self) -> float:
        now = datetime.now()
        today_target = datetime.combine(
            now.date(), dt_time(hour=self.target_hour, minute=self.target_minute)
        )
        next_target = (
            today_target + timedelta(days=1) if now >= today_target else today_target
        )
        delta = next_target - now
        secs = max(delta.total_seconds(), 0.0)
        self.logger.debug("Seconds until next run for user %s: %s", self.user_id, secs)
        return secs

    def next_run_epoch_ms(self) -> int:
        secs = self._seconds_until_next_target()
        return int((time.time() + secs) * 1000)

    def compute_next_run_dt(self) -> datetime:
        secs = self._seconds_until_next_target()
        return datetime.now() + timedelta(seconds=secs)

    def _perform_task(self):
        """
        Create per-user report via the netbank module.
        Import the heavy Selenium-based class lazily to avoid importing at module import time.
        This method is intentionally the same as previous implementation; it should be run in a
        separate thread so the scheduler worker can remain idle/sleeping.
        """
        run_started = datetime.utcnow()
        self.logger.info("Report task start (utc): %s", run_started.isoformat() + "Z")

        try:
            self.user_dir.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(str(self.user_dir), 0o700)
            except Exception:
                self.logger.debug("chmod not supported for %s", self.user_dir)
        except Exception:
            self.logger.exception("Failed to ensure user dir exists: %s", self.user_dir)
            return

        try:
            from app.core.netbank.getReport import ErsteNetBroker
        except Exception:
            self.logger.exception(
                "Failed to import ErsteNetBroker for user %s", self.user_id
            )
            return

        firebase = self._firebase_provider() if self._firebase_provider else None
        if firebase:
            try:
                firebase.set_active_user(self.user_id)
                self.logger.debug("Set Firebase active user to %s", self.user_id)
            except Exception:
                try:
                    base_dir = self.user_dir.parent
                    firebase.load_tokens_from_dir(base_dir, refresh=True)
                    firebase.set_active_user(self.user_id)
                    self.logger.debug(
                        "Loaded tokens from %s and set active user to %s",
                        base_dir,
                        self.user_id,
                    )
                except Exception:
                    self.logger.exception(
                        "Failed to set Firebase active user for %s; OTP checks may fail",
                        self.user_id,
                    )

        try:
            self.logger.debug(
                "Instantiating ErsteNetBroker for user %s (saveFolder=%s)",
                self.user_id,
                str(self.user_dir),
            )
            broker = ErsteNetBroker(user_id=self.user_id, saveFolder=str(self.user_dir))
            self.logger.info("Calling get_report() for user %s", self.user_id)
            result_filename = broker.get_report()
            if result_filename:
                fullpath = self.user_dir / result_filename
                try:
                    size = fullpath.stat().st_size
                except Exception:
                    size = None
                self.logger.info(
                    "get_report produced file=%s size=%s", result_filename, size
                )
            else:
                self.logger.warning(
                    "get_report returned no file for user %s", self.user_id
                )
        except Exception:
            self.logger.exception(
                "Exception while running get_report for user %s", self.user_id
            )


class Scheduler:
    """
    Single-worker scheduler that keeps CPU usage minimal by sleeping until the next scheduled job.
    Uses a heap for upcoming runs and a Condition to wake the worker only when needed.
    """

    def __init__(self, firebase_provider: Optional[Callable[[], Any]] = None):
        self._jobs: Dict[str, _Job] = {}
        self._heap: list[Tuple[float, int, str]] = []
        self._counter = 0
        self._cond = threading.Condition()
        self._worker: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._firebase_provider = firebase_provider
        logger.debug("Scheduler initialized")

    def _start_worker_if_needed(self):
        with self._cond:
            if not self._running:
                self._running = True
                self._worker = threading.Thread(target=self._worker_loop, daemon=True)
                self._worker.start()
                logger.debug("Scheduler worker started")
            else:
                self._cond.notify()

    def _worker_loop(self):
        logger.debug("Scheduler worker loop entered")
        while True:
            with self._cond:
                if not self._running:
                    logger.debug("Scheduler worker stopping")
                    break

                while self._heap and (self._heap[0][2] not in self._jobs):
                    heapq.heappop(self._heap)

                if not self._heap:
                    logger.debug("Scheduler worker sleeping indefinitely (no jobs)")
                    self._cond.wait()
                    continue

                next_run_ts, _, user_id = self._heap[0]
                now_ts = time.time()
                wait_secs = max(next_run_ts - now_ts, 0.0)

                if wait_secs > 0:
                    self._cond.wait(timeout=wait_secs)
                    continue

                heapq.heappop(self._heap)

            with self._lock:
                job = self._jobs.get(user_id)

            if not job:
                logger.debug(
                    "Scheduled job %s not found (may have been removed); skipping",
                    user_id,
                )
                continue

            if getattr(job, "_stopped", False):
                logger.debug("Scheduled job %s marked stopped; skipping", user_id)
                continue

            try:
                self._spawn_job_thread(job)
            except Exception:
                logger.exception("Failed to spawn job thread for user %s", user_id)

            with self._lock:
                if user_id in self._jobs:
                    next_dt = job.compute_next_run_dt()
                    with self._cond:
                        self._counter += 1
                        heapq.heappush(
                            self._heap, (next_dt.timestamp(), self._counter, user_id)
                        )
                        self._cond.notify()

    def _spawn_job_thread(self, job: _Job):
        thread = threading.Thread(target=job._perform_task, daemon=True)
        thread.start()
        logger.info(
            "Spawned background thread for user %s (thread=%s)",
            job.user_id,
            thread.name,
        )

    def start_job_for_user(
        self,
        user_id: str,
        user_dir: Path,
        target_hour: int = 18,
        target_minute: int = 0,
    ):
        logger.info(
            "Request to start job for user=%s dir=%s target=%02d:%02d",
            user_id,
            str(user_dir),
            target_hour,
            target_minute,
        )
        try:
            user_dir.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(str(user_dir), 0o700)
            except Exception:
                logger.debug("chmod may not be supported for user_dir=%s", user_dir)
        except Exception:
            logger.exception("Failed to create user_dir for user=%s", user_id)
            raise

        with self._lock:
            if user_id in self._jobs:
                logger.info("Restarting existing job for user=%s", user_id)
                try:
                    self._jobs[user_id]._stopped = True
                except Exception:
                    logger.debug(
                        "Error marking previous job stopped for user=%s", user_id
                    )
            job = _Job(
                user_id,
                user_dir,
                target_hour,
                target_minute,
                firebase_provider=self._firebase_provider,
            )
            self._jobs[user_id] = job
            next_dt = job.compute_next_run_dt()
            with self._cond:
                self._counter += 1
                heapq.heappush(
                    self._heap, (next_dt.timestamp(), self._counter, user_id)
                )
                self._start_worker_if_needed()
        logger.info("Job scheduled for user=%s", user_id)
        return job

    def get_next_run_for_user(self, user_id: str) -> Optional[Dict]:
        with self._lock:
            job = self._jobs.get(user_id)
        if not job:
            logger.debug("get_next_run_for_user: no job for user %s", user_id)
            return None
        try:
            secs = job._seconds_until_next_target()
            ts_ms = job.next_run_epoch_ms()
            return {"seconds_until_next_run": secs, "next_run_timestamp_ms": ts_ms}
        except Exception:
            logger.exception("Failed to compute next run for user %s", user_id)
            return None

    def stop_job_for_user(self, user_id: str):
        logger.info("Request to stop job for user=%s", user_id)
        with self._lock:
            job = self._jobs.pop(user_id, None)
        if job:
            try:
                job._stopped = True
                logger.info("Job stopped for user=%s", user_id)
            except Exception:
                logger.exception("Error stopping job for user=%s", user_id)
            return True
        logger.warning("No job found to stop for user=%s", user_id)
        return False

    def stop_all(self):
        logger.info("Stopping all jobs (count=%d)", len(self._jobs))
        with self._lock:
            for job in self._jobs.values():
                try:
                    job._stopped = True
                except Exception:
                    logger.debug("Failed to mark job stopped")
            self._jobs.clear()
        with self._cond:
            self._running = False
            self._cond.notify_all()
        if self._worker and self._worker.is_alive():
            self._worker.join(timeout=2.0)
        logger.debug("All jobs stopped and worker joined")

    def restore_jobs_from_dir(
        self, base_dir: Path, target_hour: int = 18, target_minute: int = 0
    ):
        base_dir = Path(base_dir)
        logger.info("Restoring jobs from directory: %s", str(base_dir))
        if not base_dir.exists():
            logger.debug("Base directory does not exist: %s", str(base_dir))
            return
        for child in base_dir.iterdir():
            if not child.is_dir():
                logger.debug("Skipping non-directory entry: %s", child)
                continue
            cred_path = child / "credentials.json"
            if not cred_path.exists():
                logger.debug("Skipping folder without credentials.json: %s", child)
                continue
            user_id = child.name
            try:
                logger.info("Restoring job for user=%s from %s", user_id, child)
                self.start_job_for_user(user_id, child, target_hour, target_minute)
            except Exception:
                logger.exception("Failed to restore job for user=%s", user_id)

    def trigger_run_for_user(self, user_id: str):
        with self._lock:
            job = self._jobs.get(user_id)

        if job:
            try:
                self._spawn_job_thread(job)
                logger.info(
                    "Triggered immediate run for user %s using existing scheduled job",
                    user_id,
                )
                return True
            except Exception:
                logger.exception("Failed to trigger existing job for user %s", user_id)
                return False

        try:
            base_data_dir = get_settings().app_user_data_dir
            user_dir = base_data_dir / user_id
            temp_job = _Job(
                user_id=user_id,
                user_dir=user_dir,
                firebase_provider=self._firebase_provider,
            )
            self._spawn_job_thread(temp_job)
            logger.info(
                "Triggered one-off immediate run for user %s (no existing schedule)",
                user_id,
            )
            return True
        except Exception:
            logger.exception("Failed to trigger one-off job for user %s", user_id)
            return False


def _acquire_scheduler_lock() -> bool:
    global _SCHED_LOCK_FD
    try:
        _SCHED_LOCK_FD = os.open(
            "/tmp/bab_scheduler.lock", os.O_RDWR | os.O_CREAT, 0o600
        )
        fcntl.lockf(_SCHED_LOCK_FD, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def create_scheduler(
    firebase_provider: Optional[Callable[[], Any]] = None,
    acquire_lock: bool = True,
) -> Optional[Scheduler]:
    if acquire_lock and not _acquire_scheduler_lock():
        logger.warning("Scheduler lock not acquired; skipping scheduler creation")
        return None
    return Scheduler(firebase_provider=firebase_provider)
