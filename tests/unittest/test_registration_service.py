"""Unit tests for register_user and unregister_user in app.services.login_service."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from app.core.exceptions import RegistrationFailedError
from app.schemas.login import RegisterRequest
from app.services.login_service import register_user, unregister_user

# ── register_user ──────────────────────────────────────────────────────────


def _make_mock_settings(tmp_path: Path) -> MagicMock:
    s = MagicMock()
    s.app_user_data_dir = tmp_path
    s.app_job_hour = 18
    s.app_job_minute = 0
    s.unregister_deletion_days = 60
    return s


def _make_mock_firebase(user_id: str = "uid_new") -> MagicMock:
    fb = MagicMock()
    auth_client = MagicMock()
    auth_client.create_user_with_email_and_password.return_value = {
        "idToken": "new_id_token",
        "refreshToken": "new_refresh",
        "localId": user_id,
    }
    fb.auth.return_value = (auth_client, None)
    fb.get_user_token.return_value = {"idToken": "new_id_token"}
    return fb, auth_client


def test_register_user_success(tmp_path):
    mock_fb, mock_auth = _make_mock_firebase()
    mock_scheduler = MagicMock()
    mock_settings = _make_mock_settings(tmp_path)

    with patch("app.services.login_service._get_settings", return_value=mock_settings):
        result = register_user(
            RegisterRequest(email="new@example.com", password="secret"),
            mock_scheduler,
            mock_fb,
        )

    assert result.access_token == "new_id_token"
    assert result.user_id == "uid_new"
    assert result.message == "Registration successful"

    # credentials.json written
    cred_path = tmp_path / "uid_new" / "credentials.json"
    assert cred_path.exists()
    data = json.loads(cred_path.read_text())
    assert data["idToken"] == "new_id_token"
    assert data["email"] == "new@example.com"

    # scheduler job started
    mock_scheduler.start_job_for_user.assert_called_once()
    # tokens registered
    mock_fb.register_user_tokens.assert_called_once()


def test_register_user_fallback_user_id_from_email(tmp_path):
    mock_fb = MagicMock()
    auth_client = MagicMock()
    auth_client.create_user_with_email_and_password.return_value = {
        "idToken": "tok",
        "refreshToken": "ref",
        # No userId / localId / uid field
    }
    mock_fb.auth.return_value = (auth_client, None)
    mock_settings = _make_mock_settings(tmp_path)

    with patch("app.services.login_service._get_settings", return_value=mock_settings):
        result = register_user(
            RegisterRequest(email="test@example.com", password="pw"),
            MagicMock(),
            mock_fb,
        )

    assert result.user_id.startswith("user_")
    assert "example" in result.user_id


def test_register_user_raises_registration_failed_on_error(tmp_path):
    mock_fb = MagicMock()
    auth_client = MagicMock()
    auth_client.create_user_with_email_and_password.side_effect = RuntimeError(
        "firebase down"
    )
    mock_fb.auth.return_value = (auth_client, None)
    mock_settings = _make_mock_settings(tmp_path)

    with patch("app.services.login_service._get_settings", return_value=mock_settings):
        with pytest.raises(RegistrationFailedError):
            register_user(
                RegisterRequest(email="err@example.com", password="pw"),
                MagicMock(),
                mock_fb,
            )


def test_register_user_raises_when_no_id_token(tmp_path):
    mock_fb = MagicMock()
    auth_client = MagicMock()
    auth_client.create_user_with_email_and_password.return_value = {
        "refreshToken": "ref",
        "localId": "uid123",
        # idToken missing
    }
    mock_fb.auth.return_value = (auth_client, None)
    mock_settings = _make_mock_settings(tmp_path)

    with patch("app.services.login_service._get_settings", return_value=mock_settings):
        with pytest.raises(RegistrationFailedError):
            register_user(
                RegisterRequest(email="notoken@example.com", password="pw"),
                MagicMock(),
                mock_fb,
            )


def test_register_user_raises_when_no_refresh_token(tmp_path):
    mock_fb = MagicMock()
    auth_client = MagicMock()
    auth_client.create_user_with_email_and_password.return_value = {
        "idToken": "tok",
        "localId": "uid123",
        # refreshToken missing
    }
    mock_fb.auth.return_value = (auth_client, None)
    mock_settings = _make_mock_settings(tmp_path)

    with patch("app.services.login_service._get_settings", return_value=mock_settings):
        with pytest.raises(RegistrationFailedError):
            register_user(
                RegisterRequest(email="noref@example.com", password="pw"),
                MagicMock(),
                mock_fb,
            )


# ── unregister_user ────────────────────────────────────────────────────────


def test_unregister_user_stops_job_and_schedules_deletion(tmp_path):
    mock_scheduler = MagicMock()
    mock_fb = MagicMock()
    mock_fb.get_user_token.return_value = None
    mock_settings = _make_mock_settings(tmp_path)

    uid = "user_unreg"
    user_dir = tmp_path / uid
    user_dir.mkdir()
    cred_file = user_dir / "credentials.json"
    cred_file.write_text('{"idToken": "x"}')

    with patch("app.services.login_service._get_settings", return_value=mock_settings):
        response = unregister_user(uid, mock_scheduler, mock_fb)

    # Job stopped
    mock_scheduler.stop_job_for_user.assert_called_once_with(uid)
    # credentials removed
    assert not cred_file.exists()
    # deletion pending file created
    assert (user_dir / "deletion_pending.json").exists()
    # token cleared
    mock_fb.clear_user.assert_called_once_with(uid)
    # response
    assert "unregistered" in response.message.lower()
    assert "60" in response.message
    assert response.deletion_at_ms > response.deletion_scheduled_at_ms


def test_unregister_user_respects_deletion_days_setting(tmp_path):
    mock_settings = _make_mock_settings(tmp_path)
    mock_settings.unregister_deletion_days = 30

    uid = "user_days"
    (tmp_path / uid).mkdir()

    with patch("app.services.login_service._get_settings", return_value=mock_settings):
        response = unregister_user(uid, MagicMock(), MagicMock())

    expected_delta_ms = 30 * 24 * 60 * 60 * 1000
    assert (
        response.deletion_at_ms - response.deletion_scheduled_at_ms == expected_delta_ms
    )


def test_unregister_user_empty_user_id_raises():
    with pytest.raises(ValueError, match="User not found"):
        unregister_user("", MagicMock(), MagicMock())


def test_unregister_user_no_credentials_file_still_succeeds(tmp_path):
    """unregister_user should succeed even if credentials.json doesn't exist."""
    mock_settings = _make_mock_settings(tmp_path)
    uid = "user_nocred"
    (tmp_path / uid).mkdir()

    with patch("app.services.login_service._get_settings", return_value=mock_settings):
        response = unregister_user(uid, MagicMock(), MagicMock())

    assert response.deletion_at_ms > 0


# ── login cancels pending deletion ────────────────────────────────────────


def test_login_cancels_pending_deletion(tmp_path):
    """Re-logging in while a deletion is pending should cancel it."""
    from app.schemas.login import LoginRequest
    from app.services.login_service import login_user
    from app.services.user_deletion_service import schedule_user_deletion

    uid = "user_relogin"
    user_dir = tmp_path / uid
    user_dir.mkdir()
    # plant a deletion pending
    schedule_user_deletion(user_dir, uid, 60)
    assert (user_dir / "deletion_pending.json").exists()

    mock_fb = MagicMock()
    auth_client = MagicMock()
    auth_client.sign_in_with_email_and_password.return_value = {
        "idToken": "tok",
        "refreshToken": "ref",
        "localId": uid,
    }
    mock_fb.auth.return_value = (auth_client, None)
    mock_fb.get_user_token.return_value = None

    mock_settings = _make_mock_settings(tmp_path)

    with patch("app.services.login_service._get_settings", return_value=mock_settings):
        result = login_user(
            LoginRequest(email="relogin@example.com", password="pw"),
            MagicMock(),
            mock_fb,
        )

    assert result.access_token == "tok"
    assert not (user_dir / "deletion_pending.json").exists()
