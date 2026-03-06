"""Additional tests for app.services.login_service – login_user, logout_user."""

import os
from unittest.mock import MagicMock

import pytest

# Ensure test env before any app imports
os.environ.setdefault("PYTEST_RUNNING", "1")
os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

from app.core.exceptions import LoginFailedError
from app.schemas.login import LoginRequest
from app.services.login_service import login_user, logout_user


def _reset_settings(tmp_path, monkeypatch):
    """Reset the settings cache so APP_USER_DATA_DIR monkeypatch takes effect."""
    import app.core.config as cfg

    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))
    cfg._SETTINGS = None


# ── login_user – success path ─────────────────────────────────────────────


def test_login_user_success(tmp_path, monkeypatch):
    _reset_settings(tmp_path, monkeypatch)

    mock_auth_client = MagicMock()
    mock_auth_client.sign_in_with_email_and_password.return_value = {
        "idToken": "id_tok_123",
        "refreshToken": "ref_tok_456",
        "localId": "user_abc",
    }

    mock_firebase = MagicMock()
    mock_firebase.auth.return_value = (mock_auth_client, None)

    mock_scheduler = MagicMock()

    data = LoginRequest(email="test@example.com", password="pw123")

    try:
        resp = login_user(data, mock_scheduler, mock_firebase)
        assert resp.access_token == "id_tok_123"
        assert resp.message == "Login successful"
        mock_scheduler.start_job_for_user.assert_called_once()
    finally:
        import app.core.config as cfg

        cfg._SETTINGS = None


def test_login_user_missing_id_token_raises(tmp_path, monkeypatch):
    _reset_settings(tmp_path, monkeypatch)

    mock_auth_client = MagicMock()
    mock_auth_client.sign_in_with_email_and_password.return_value = {
        "refreshToken": "ref",
        "localId": "user1",
        # no idToken
    }
    mock_firebase = MagicMock()
    mock_firebase.auth.return_value = (mock_auth_client, None)

    data = LoginRequest(email="user@example.com", password="bad")

    try:
        with pytest.raises(LoginFailedError, match="Login failed"):
            login_user(data, MagicMock(), mock_firebase)
    finally:
        import app.core.config as cfg

        cfg._SETTINGS = None


def test_login_user_fallback_user_id(tmp_path, monkeypatch):
    """If no userId/localId in response, derive from email."""
    _reset_settings(tmp_path, monkeypatch)

    mock_auth_client = MagicMock()
    mock_auth_client.sign_in_with_email_and_password.return_value = {
        "idToken": "tok",
        "refreshToken": "ref",
        # no user id fields
    }
    mock_firebase = MagicMock()
    mock_firebase.auth.return_value = (mock_auth_client, None)
    mock_scheduler = MagicMock()

    data = LoginRequest(email="fallback@example.com", password="pw")

    try:
        resp = login_user(data, mock_scheduler, mock_firebase)
        assert resp.access_token == "tok"
        # user_id was derived from email
        call_args = mock_scheduler.start_job_for_user.call_args
        derived_uid = call_args[0][0]
        assert "fallback" in derived_uid.lower() or "example" in derived_uid.lower()
    finally:
        import app.core.config as cfg

        cfg._SETTINGS = None


# ── logout_user ───────────────────────────────────────────────────────────


def test_logout_user_success(tmp_path, monkeypatch):
    _reset_settings(tmp_path, monkeypatch)

    user_dir = tmp_path / "user1"
    user_dir.mkdir()
    cred_file = user_dir / "credentials.json"
    cred_file.write_text("{}")

    mock_scheduler = MagicMock()
    mock_firebase = MagicMock()

    try:
        result = logout_user("user1", mock_scheduler, mock_firebase)
        assert result is True
        mock_scheduler.stop_job_for_user.assert_called_once_with("user1")
        mock_firebase.clear_user.assert_called_once_with("user1")
        assert not cred_file.exists()
    finally:
        import app.core.config as cfg

        cfg._SETTINGS = None


def test_logout_user_empty_user_id_raises(monkeypatch, tmp_path):
    _reset_settings(tmp_path, monkeypatch)
    try:
        with pytest.raises(ValueError, match="User not found"):
            logout_user("", MagicMock(), MagicMock())
    finally:
        import app.core.config as cfg

        cfg._SETTINGS = None


def test_logout_user_no_credentials_file(tmp_path, monkeypatch):
    """logout_user should succeed even if credentials file doesn't exist."""
    _reset_settings(tmp_path, monkeypatch)
    mock_scheduler = MagicMock()
    mock_firebase = MagicMock()

    try:
        result = logout_user("no_such_user", mock_scheduler, mock_firebase)
        assert result is True
        mock_firebase.clear_user.assert_called_once_with("no_such_user")
    finally:
        import app.core.config as cfg

        cfg._SETTINGS = None
