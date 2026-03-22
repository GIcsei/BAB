"""Unit tests for app.services.user_deletion_service."""

import json
import time
from unittest.mock import patch

from app.services.user_deletion_service import (
    cancel_user_deletion,
    execute_expired_deletions,
    get_pending_deletion,
    schedule_user_deletion,
)

# ── schedule_user_deletion ─────────────────────────────────────────────────


def test_schedule_creates_deletion_pending_file(tmp_path):
    user_dir = tmp_path / "user1"
    user_dir.mkdir()
    result = schedule_user_deletion(user_dir, "user1", 60)

    pending_file = user_dir / "deletion_pending.json"
    assert pending_file.exists()

    data = json.loads(pending_file.read_text())
    assert data["user_id"] == "user1"
    assert data["deletion_at_ms"] > data["requested_at_ms"]
    assert result["deletion_at_ms"] == data["deletion_at_ms"]
    assert result["requested_at_ms"] == data["requested_at_ms"]


def test_schedule_deletion_at_correct_offset(tmp_path):
    user_dir = tmp_path / "user_offset"
    user_dir.mkdir()
    days = 60
    before_ms = int(time.time() * 1000)
    result = schedule_user_deletion(user_dir, "user_offset", days)
    after_ms = int(time.time() * 1000)

    expected_delta_ms = days * 24 * 60 * 60 * 1000
    assert result["deletion_at_ms"] - result["requested_at_ms"] == expected_delta_ms
    assert before_ms <= result["requested_at_ms"] <= after_ms


def test_schedule_configurable_days(tmp_path):
    user_dir = tmp_path / "user_days"
    user_dir.mkdir()
    result = schedule_user_deletion(user_dir, "user_days", 30)
    expected_delta_ms = 30 * 24 * 60 * 60 * 1000
    assert result["deletion_at_ms"] - result["requested_at_ms"] == expected_delta_ms


# ── cancel_user_deletion ───────────────────────────────────────────────────


def test_cancel_removes_pending_file(tmp_path):
    user_dir = tmp_path / "user_cancel"
    user_dir.mkdir()
    schedule_user_deletion(user_dir, "user_cancel", 60)

    result = cancel_user_deletion(user_dir)

    assert result is True
    assert not (user_dir / "deletion_pending.json").exists()


def test_cancel_returns_false_when_no_pending(tmp_path):
    user_dir = tmp_path / "user_no_pending"
    user_dir.mkdir()
    assert cancel_user_deletion(user_dir) is False


# ── get_pending_deletion ───────────────────────────────────────────────────


def test_get_pending_deletion_returns_data(tmp_path):
    user_dir = tmp_path / "user_get"
    user_dir.mkdir()
    schedule_user_deletion(user_dir, "user_get", 60)

    data = get_pending_deletion(user_dir)
    assert data is not None
    assert data["user_id"] == "user_get"


def test_get_pending_deletion_returns_none_when_absent(tmp_path):
    user_dir = tmp_path / "user_none"
    user_dir.mkdir()
    assert get_pending_deletion(user_dir) is None


def test_get_pending_deletion_returns_none_on_corrupt_file(tmp_path):
    user_dir = tmp_path / "user_corrupt"
    user_dir.mkdir()
    (user_dir / "deletion_pending.json").write_text("not valid json{{{")

    assert get_pending_deletion(user_dir) is None


# ── execute_expired_deletions ──────────────────────────────────────────────


def test_execute_deletes_expired_user_directory(tmp_path):
    base_dir = tmp_path / "data"
    base_dir.mkdir()
    user_dir = base_dir / "expired_user"
    user_dir.mkdir()

    # Set deletion_at_ms in the past
    past_ms = int(time.time() * 1000) - 1000
    record = {
        "user_id": "expired_user",
        "requested_at_ms": past_ms - 1000,
        "deletion_at_ms": past_ms,
    }
    (user_dir / "deletion_pending.json").write_text(json.dumps(record))

    deleted = execute_expired_deletions(base_dir)
    assert deleted == 1
    assert not user_dir.exists()


def test_execute_does_not_delete_future_deletion(tmp_path):
    base_dir = tmp_path / "data"
    base_dir.mkdir()
    user_dir = base_dir / "active_user"
    user_dir.mkdir()

    schedule_user_deletion(user_dir, "active_user", 60)

    deleted = execute_expired_deletions(base_dir)
    assert deleted == 0
    assert user_dir.exists()


def test_execute_does_not_delete_users_without_pending(tmp_path):
    base_dir = tmp_path / "data"
    base_dir.mkdir()
    user_dir = base_dir / "normal_user"
    user_dir.mkdir()
    (user_dir / "credentials.json").write_text("{}")

    deleted = execute_expired_deletions(base_dir)
    assert deleted == 0
    assert user_dir.exists()


def test_execute_returns_zero_when_base_dir_missing(tmp_path):
    non_existent = tmp_path / "no_such_dir"
    assert execute_expired_deletions(non_existent) == 0


def test_execute_multi_user_isolation(tmp_path):
    """Expired user is deleted; active user is untouched."""
    base_dir = tmp_path / "data"
    base_dir.mkdir()

    # expired user
    expired_dir = base_dir / "user_expired"
    expired_dir.mkdir()
    past_ms = int(time.time() * 1000) - 1000
    (expired_dir / "deletion_pending.json").write_text(
        json.dumps(
            {
                "user_id": "user_expired",
                "requested_at_ms": past_ms - 1000,
                "deletion_at_ms": past_ms,
            }
        )
    )

    # active user (future deletion)
    active_dir = base_dir / "user_active"
    active_dir.mkdir()
    schedule_user_deletion(active_dir, "user_active", 60)

    deleted = execute_expired_deletions(base_dir)
    assert deleted == 1
    assert not expired_dir.exists()
    assert active_dir.exists()


def test_execute_handles_rmtree_failure_gracefully(tmp_path):
    """execute_expired_deletions logs but does not raise if rmtree fails."""
    base_dir = tmp_path / "data"
    base_dir.mkdir()
    user_dir = base_dir / "fail_user"
    user_dir.mkdir()
    past_ms = int(time.time() * 1000) - 1000
    (user_dir / "deletion_pending.json").write_text(
        json.dumps(
            {
                "user_id": "fail_user",
                "requested_at_ms": past_ms - 1000,
                "deletion_at_ms": past_ms,
            }
        )
    )

    with patch(
        "app.services.user_deletion_service.shutil.rmtree",
        side_effect=OSError("permission denied"),
    ):
        deleted = execute_expired_deletions(base_dir)

    # Failed deletion should not count, and function should not raise
    assert deleted == 0
