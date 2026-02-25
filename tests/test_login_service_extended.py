"""Additional tests for app.services.login_service – get_firebase, login_user."""

import os
from unittest.mock import MagicMock, patch

import pytest

# Ensure test env before any app imports
os.environ.setdefault("PYTEST_RUNNING", "1")
os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

from app.services.login_service import get_firebase

# ── get_firebase – singleton ───────────────────────────────────────────────


def test_get_firebase_returns_instance():
    """get_firebase() should return a Firebase instance (singleton)."""
    fb = get_firebase()
    assert fb is not None


def test_get_firebase_is_singleton():
    fb1 = get_firebase()
    fb2 = get_firebase()
    assert fb1 is fb2


# ── login_user – mocked ────────────────────────────────────────────────────


def test_login_user_success(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))

    mock_auth_client = MagicMock()
    mock_auth_client.sign_in_with_email_and_password.return_value = {
        "idToken": "id_tok_123",
        "refreshToken": "ref_tok_456",
        "localId": "user_abc",
    }

    mock_firebase = MagicMock()
    mock_firebase.auth.return_value = (mock_auth_client, None)

    mock_scheduler = MagicMock()

    from app.schemas.login import LoginRequest

    data = LoginRequest(email="test@example.com", password="pw123")

    with (
        patch("app.services.login_service.get_firebase", return_value=mock_firebase),
        patch("app.services.login_service.scheduler", mock_scheduler),
    ):
        from app.services.login_service import login_user

        resp = login_user(data)

    assert resp.access_token == "id_tok_123"
    assert resp.message == "Login successful"
    mock_scheduler.start_job_for_user.assert_called_once()


def test_login_user_missing_id_token_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))

    mock_auth_client = MagicMock()
    mock_auth_client.sign_in_with_email_and_password.return_value = {
        "refreshToken": "ref",
        "localId": "user1",
        # no idToken
    }
    mock_firebase = MagicMock()
    mock_firebase.auth.return_value = (mock_auth_client, None)

    from app.schemas.login import LoginRequest

    data = LoginRequest(email="user@example.com", password="bad")

    with (
        patch("app.services.login_service.get_firebase", return_value=mock_firebase),
        patch("app.services.login_service.scheduler", MagicMock()),
    ):
        from app.services.login_service import login_user

        with pytest.raises(ValueError, match="Login failed"):
            login_user(data)


def test_login_user_fallback_user_id(tmp_path, monkeypatch):
    """If no userId/localId in response, derive from email."""
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))

    mock_auth_client = MagicMock()
    mock_auth_client.sign_in_with_email_and_password.return_value = {
        "idToken": "tok",
        "refreshToken": "ref",
        # no user id fields
    }
    mock_firebase = MagicMock()
    mock_firebase.auth.return_value = (mock_auth_client, None)
    mock_scheduler = MagicMock()

    from app.schemas.login import LoginRequest

    data = LoginRequest(email="fallback@example.com", password="pw")

    with (
        patch("app.services.login_service.get_firebase", return_value=mock_firebase),
        patch("app.services.login_service.scheduler", mock_scheduler),
    ):
        from app.services.login_service import login_user

        resp = login_user(data)

    assert resp.access_token == "tok"
    # user_id was derived from email
    call_args = mock_scheduler.start_job_for_user.call_args
    derived_uid = call_args[0][0]
    assert "fallback" in derived_uid.lower() or "example" in derived_uid.lower()
