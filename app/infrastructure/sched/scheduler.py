import heapq
import logging
import os
import threading
import time
from contextlib import suppress
from datetime import datetime, timedelta
from datetime import time as dt_time
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, Optional, Tuple, cast

fcntl: Optional[ModuleType]
try:
    import fcntl as _fcntl

    fcntl = _fcntl
except ImportError:  # pragma: no cover
    fcntl = None

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_SCHED_LOCK_PATH = "/tmp/bab_scheduler.lock"
_DEFAULT_LEADER_POLL_SECONDS = 5.0


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
    ) -> None:
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

    def _perform_task(self) -> None:
        run_started = datetime.now()
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

    def __init__(
        self,
        firebase_provider: Optional[Callable[[], Any]] = None,
        base_dir: Optional[Path] = None,
        target_hour: int = 18,
        target_minute: int = 0,
        acquire_lock: bool = True,
        leader_poll_seconds: float = _DEFAULT_LEADER_POLL_SECONDS,
    ) -> None:
        self._jobs: Dict[str, _Job] = {}
        self._heap: list[Tuple[float, int, str]] = []
        self._counter = 0
        self._cond = threading.Condition()
        self._worker: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._firebase_provider = firebase_provider

        self._base_dir = (
            Path(base_dir) if base_dir is not None else get_settings().app_user_data_dir
        )
        self._target_hour = int(target_hour)
        self._target_minute = int(target_minute)
        self._acquire_lock = acquire_lock
        self._leader_poll_seconds = float(leader_poll_seconds)

        self._leader_thread: Optional[threading.Thread] = None
        self._leader_running = False
        self._leader_stop_event = threading.Event()
        self._leader_lock_fd: Optional[int] = None
        self._is_leader = False

        logger.debug(
            "Scheduler initialized base_dir=%s target=%02d:%02d acquire_lock=%s",
            self._base_dir,
            self._target_hour,
            self._target_minute,
            self._acquire_lock,
        )

    def start(self) -> None:
        with self._lock:
            if self._leader_running:
                return
            self._leader_running = True
            self._leader_stop_event.clear()
            self._leader_thread = threading.Thread(
                target=self._leader_loop,
                daemon=True,
                name="scheduler-leader-monitor",
            )
            self._leader_thread.start()
        logger.info("Scheduler leader monitor started")

    def _leader_loop(self) -> None:
        logger.debug("Scheduler leader loop entered")
        while not self._leader_stop_event.is_set():
            became_leader = self._try_acquire_leadership()
            if became_leader:
                self._on_became_leader()
                self._reconcile_jobs_from_dir(
                    self._base_dir,
                    self._target_hour,
                    self._target_minute,
                )
            self._leader_stop_event.wait(timeout=self._leader_poll_seconds)
        logger.debug("Scheduler leader loop exiting")

    def _try_acquire_leadership(self) -> bool:
        if self._is_leader:
            return True

        if not self._acquire_lock:
            self._is_leader = True
            logger.info("Scheduler leadership acquired (lock disabled)")
            return True

        if fcntl is None:
            logger.warning(
                "fcntl not available; scheduler leadership lock disabled for this platform"
            )
            self._is_leader = True
            return True

        fcntl_mod = cast(Any, fcntl)
        try:
            if self._leader_lock_fd is None:
                self._leader_lock_fd = os.open(
                    _SCHED_LOCK_PATH,
                    os.O_RDWR | os.O_CREAT,
                    0o600,
                )
            fcntl_mod.lockf(
                self._leader_lock_fd,
                fcntl_mod.LOCK_EX | fcntl_mod.LOCK_NB,
            )
            self._is_leader = True
            logger.info("Scheduler leadership acquired")
            return True
        except OSError:
            return False

    def _release_leadership(self) -> None:
        if not self._is_leader:
            return

        if fcntl is not None and self._leader_lock_fd is not None:
            fcntl_mod = cast(Any, fcntl)
            with suppress(OSError):
                fcntl_mod.lockf(self._leader_lock_fd, fcntl_mod.LOCK_UN)

        if self._leader_lock_fd is not None:
            with suppress(OSError):
                os.close(self._leader_lock_fd)

        self._leader_lock_fd = None
        self._is_leader = False
        logger.info("Scheduler leadership released")

    def _on_became_leader(self) -> None:
        if self._running:
            return
        logger.info("This process is scheduler leader")
        self.restore_jobs_from_dir(
            self._base_dir,
            self._target_hour,
            self._target_minute,
        )

    def _discover_user_dirs(self, base_dir: Path) -> Dict[str, Path]:
        users: Dict[str, Path] = {}
        if not base_dir.exists():
            return users

        for child in base_dir.iterdir():
            if not child.is_dir():
                continue
            if not (child / "credentials.json").exists():
                continue
            users[child.name] = child

        return users

    def _reconcile_jobs_from_dir(
        self,
        base_dir: Path,
        target_hour: int,
        target_minute: int,
    ) -> None:
        if not self._is_leader:
            return

        expected_users = self._discover_user_dirs(base_dir)
        with self._lock:
            active_users = set(self._jobs.keys())

        for user_id, user_dir in expected_users.items():
            if user_id not in active_users:
                self.start_job_for_user(
                    user_id,
                    user_dir,
                    target_hour,
                    target_minute,
                )

        for user_id in active_users:
            if user_id not in expected_users:
                self.stop_job_for_user(user_id)

    def _start_worker_if_needed(self) -> None:
        with self._cond:
            if not self._running:
                self._running = True
                self._worker = threading.Thread(target=self._worker_loop, daemon=True)
                self._worker.start()
                logger.debug("Scheduler worker started")
            else:
                self._cond.notify()

    def _worker_loop(self) -> None:
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

    def _spawn_job_thread(self, job: _Job) -> None:
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
    ) -> _Job:
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

        if not self._is_leader:
            logger.info(
                "Deferring in-process scheduling for user=%s; leader will reconcile from disk",
                user_id,
            )
            return _Job(
                user_id=user_id,
                user_dir=user_dir,
                target_hour=target_hour,
                target_minute=target_minute,
                firebase_provider=self._firebase_provider,
            )

        with self._lock:
            if user_id in self._jobs:
                existing_job = self._jobs[user_id]
                if not getattr(existing_job, "_stopped", False):
                    logger.info(
                        "Job already active for user=%s; skipping duplicate schedule",
                        user_id,
                    )
                    return existing_job
                logger.info("Replacing stopped job for user=%s", user_id)

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

    def get_next_run_for_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(user_id)

        if not job:
            settings = get_settings()
            user_dir = settings.app_user_data_dir / user_id
            if not (user_dir / "credentials.json").exists():
                logger.debug("get_next_run_for_user: no job for user %s", user_id)
                return None

            job = _Job(
                user_id=user_id,
                user_dir=user_dir,
                target_hour=settings.app_job_hour,
                target_minute=settings.app_job_minute,
                firebase_provider=self._firebase_provider,
            )

        try:
            secs = job._seconds_until_next_target()
            ts_ms = job.next_run_epoch_ms()
            return {"seconds_until_next_run": secs, "next_run_timestamp_ms": ts_ms}
        except Exception:
            logger.exception("Failed to compute next run for user %s", user_id)
            return None

    def stop_job_for_user(self, user_id: str) -> bool:
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

    def stop_all(self) -> None:
        logger.info("Stopping scheduler and all jobs (count=%d)", len(self._jobs))

        with self._lock:
            self._leader_running = False
        self._leader_stop_event.set()

        if self._leader_thread and self._leader_thread.is_alive():
            self._leader_thread.join(timeout=2.0)

        self._release_leadership()

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

        logger.debug("Scheduler stopped")

    def restore_jobs_from_dir(
        self,
        base_dir: Path,
        target_hour: int = 18,
        target_minute: int = 0,
    ) -> None:
        if not self._is_leader:
            logger.debug("Skipping restore_jobs_from_dir because process is not leader")
            return

        base_dir = Path(base_dir)
        logger.info("Restoring jobs from directory: %s", str(base_dir))
        if not base_dir.exists():
            logger.debug("Base directory does not exist: %s", str(base_dir))
            return

        for user_id, child in self._discover_user_dirs(base_dir).items():
            try:
                logger.info("Restoring job for user=%s from %s", user_id, child)
                self.start_job_for_user(user_id, child, target_hour, target_minute)
            except Exception:
                logger.exception("Failed to restore job for user=%s", user_id)

    def trigger_run_for_user(self, user_id: str) -> bool:
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


def create_scheduler(
    firebase_provider: Optional[Callable[[], Any]] = None,
    acquire_lock: bool = True,
) -> Optional["Scheduler"]:
    settings = get_settings()
    scheduler = Scheduler(
        firebase_provider=firebase_provider,
        base_dir=settings.app_user_data_dir,
        target_hour=settings.app_job_hour,
        target_minute=settings.app_job_minute,
        acquire_lock=acquire_lock,
    )
    scheduler.start()
    return scheduler
