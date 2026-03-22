"""Service for scheduling and executing deferred user deletion."""

import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_DELETION_PENDING_FILENAME = "deletion_pending.json"


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
