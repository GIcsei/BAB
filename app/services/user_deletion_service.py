"""Service for scheduling and executing deferred user deletion."""

import json
import logging
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_DELETION_PENDING_FILENAME = "deletion_pending.json"
_DEFAULT_CHECK_INTERVAL_SECONDS = 24 * 60 * 60  # 24 hours


def schedule_user_deletion(user_dir: Path, user_id: str, days: int) -> Dict[str, int]:
    """
    Write a deletion_pending.json into the user directory.

    Returns a dict with requested_at_ms and deletion_at_ms.
    """
    requested_at_ms = int(time.time() * 1000)
    deletion_at_ms = requested_at_ms + int(days * 24 * 60 * 60 * 1000)

    record: Dict[str, Any] = {
        "user_id": user_id,
        "requested_at_ms": requested_at_ms,
        "deletion_at_ms": deletion_at_ms,
    }
    pending_path = user_dir / _DELETION_PENDING_FILENAME
    with open(pending_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh)

    logger.info(
        "Deletion scheduled for user %s in %d days (deletion_at_ms=%d)",
        user_id,
        days,
        deletion_at_ms,
    )
    return {"requested_at_ms": requested_at_ms, "deletion_at_ms": deletion_at_ms}


def cancel_user_deletion(user_dir: Path) -> bool:
    """
    Remove the deletion_pending.json file, cancelling the scheduled deletion.

    Returns True if a pending deletion was cancelled, False if none existed.
    """
    pending_path = user_dir / _DELETION_PENDING_FILENAME
    if pending_path.exists():
        pending_path.unlink()
        logger.info("Deletion cancelled for user in directory %s", user_dir)
        return True
    return False


def get_pending_deletion(user_dir: Path) -> Optional[Dict[str, Any]]:
    """
    Return the parsed deletion_pending.json for the user, or None if absent.
    """
    pending_path = user_dir / _DELETION_PENDING_FILENAME
    if not pending_path.exists():
        return None
    try:
        with open(pending_path, "r", encoding="utf-8") as fh:
            return dict(json.load(fh))
    except Exception:
        logger.exception("Failed to read deletion_pending.json at %s", pending_path)
        return None


def execute_expired_deletions(base_dir: Path) -> int:
    """
    Scan all user sub-directories under base_dir.  For each user whose
    deletion_pending.json has a deletion_at_ms in the past, delete the
    entire user directory.

    Returns the number of user directories that were deleted.
    """
    if not base_dir.exists():
        return 0

    now_ms = int(time.time() * 1000)
    deleted_count = 0

    for child in base_dir.iterdir():
        if not child.is_dir():
            continue
        record = get_pending_deletion(child)
        if record is None:
            continue
        deletion_at_ms = record.get("deletion_at_ms")
        if not isinstance(deletion_at_ms, int):
            continue
        if now_ms >= deletion_at_ms:
            user_id = record.get("user_id", child.name)
            try:
                shutil.rmtree(child)
                logger.info(
                    "Deleted expired user data for user_id=%s (directory=%s)",
                    user_id,
                    child,
                )
                deleted_count += 1
            except Exception:
                logger.exception(
                    "Failed to delete user directory %s for user_id=%s",
                    child,
                    user_id,
                )

    return deleted_count


class DeletionWorker:
    """
    Background daemon that periodically calls execute_expired_deletions().

    Runs in its own thread independently of the FastAPI request lifecycle.
    The check interval defaults to 24 hours and is configurable at construction
    time (e.g. set to a short interval in tests).
    """

    def __init__(
        self,
        base_dir: Path,
        check_interval_seconds: float = _DEFAULT_CHECK_INTERVAL_SECONDS,
    ) -> None:
        self._base_dir = Path(base_dir)
        self._check_interval_seconds = check_interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the background deletion worker thread (idempotent)."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="deletion-worker",
        )
        self._thread.start()
        logger.info(
            "DeletionWorker started (base_dir=%s, interval=%ds)",
            self._base_dir,
            self._check_interval_seconds,
        )

    def stop(self) -> None:
        """Signal the worker to stop and wait for it to exit."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("DeletionWorker stopped")

    def _run(self) -> None:
        logger.debug("DeletionWorker loop entered")
        while not self._stop_event.is_set():
            try:
                deleted = execute_expired_deletions(self._base_dir)
                if deleted:
                    logger.info(
                        "DeletionWorker: removed %d expired user account(s)", deleted
                    )
            except Exception:
                logger.exception("DeletionWorker: unexpected error during scan")

            # Sleep for the configured interval, but wake immediately on stop
            self._stop_event.wait(timeout=self._check_interval_seconds)
        logger.debug("DeletionWorker loop exiting")
