"""Tests for app.services.login_service – _extract_user_id and logout_user."""

from unittest.mock import MagicMock, patch

import pytest
from app.services.login_service import _extract_user_id, logout_user

# ── _extract_user_id ───────────────────────────────────────────────────────


def test_extract_user_id_user_id_key():
    assert _extract_user_id({"userId": "abc"}) == "abc"


def test_extract_user_id_local_id_key():
    assert _extract_user_id({"localId": "xyz"}) == "xyz"


def test_extract_user_id_user_id_snake():
    assert _extract_user_id({"user_id": "qqq"}) == "qqq"


def test_extract_user_id_uid():
    assert _extract_user_id({"uid": "uid123"}) == "uid123"


def test_extract_user_id_priority_order():
    # userId should take priority over localId
    result = _extract_user_id({"userId": "first", "localId": "second"})
    assert result == "first"


def test_extract_user_id_none_when_empty():
    result = _extract_user_id({})
    assert result is None


def test_extract_user_id_none_when_all_none():
    result = _extract_user_id(
        {"userId": None, "localId": None, "user_id": None, "uid": None}
    )
    assert result is None


# ── logout_user ────────────────────────────────────────────────────────────


def test_logout_user_empty_user_id_raises():
    with pytest.raises(ValueError, match="User not found"):
        logout_user("", MagicMock(), MagicMock())


def test_logout_user_removes_credentials(tmp_path, monkeypatch):
    """logout_user should stop job, remove cred file, clear firebase registry."""
    uid = "testuser"

    # Create a fake credential file
    user_dir = tmp_path / uid
    user_dir.mkdir()
    cred_file = user_dir / "credentials.json"
    cred_file.write_text('{"idToken": "tok"}')

    mock_scheduler = MagicMock()
    mock_firebase = MagicMock()
    mock_settings = MagicMock()
    mock_settings.app_user_data_dir = tmp_path

    with patch("app.services.login_service._get_settings", return_value=mock_settings):
        result = logout_user(uid, mock_scheduler, mock_firebase)

    assert result is True
    assert not cred_file.exists()
    mock_scheduler.stop_job_for_user.assert_called_once_with(uid)
    mock_firebase.clear_user.assert_called_once_with(uid)


def test_logout_user_no_cred_file(tmp_path, monkeypatch):
    """logout_user should succeed even when credentials.json doesn't exist."""
    uid = "no_cred_user"

    mock_scheduler = MagicMock()
    mock_firebase = MagicMock()
    mock_settings = MagicMock()
    mock_settings.app_user_data_dir = tmp_path

    with patch("app.services.login_service._get_settings", return_value=mock_settings):
        result = logout_user(uid, mock_scheduler, mock_firebase)

    assert result is True
