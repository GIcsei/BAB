"""Tests for remaining login_service and firebase_init coverage."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── login_service – chmod exception on user_dir (lines 91-92) ────────────


def test_login_user_chmod_user_dir_fails(tmp_path, monkeypatch):
    """login_user handles chmod failure on user_dir."""
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))

    from app.schemas.login import LoginRequest
    from app.services.login_service import login_user

    mock_firebase = MagicMock()
    mock_firebase.auth.return_value = (MagicMock(), None)
    mock_firebase.register_user_tokens = MagicMock()

    mock_user = {
        "idToken": "tok",
        "refreshToken": "ref",
        "localId": "u1",
    }
    mock_auth_client = MagicMock()
    mock_auth_client.sign_in_with_email_and_password.return_value = mock_user
    mock_firebase.auth.return_value = (mock_auth_client, None)

    mock_scheduler = MagicMock()

    with (
        patch("app.services.login_service.get_firebase", return_value=mock_firebase),
        patch(
            "app.services.login_service.os.chmod",
            side_effect=OSError("chmod unsupported"),
        ),
        patch("app.services.login_service.scheduler", mock_scheduler),
    ):
        data = LoginRequest(email="user@example.com", password="pw")
        result = login_user(data)

    assert result.access_token == "tok"


# ── login_service – chmod exception on cred_path (lines 106-107) ──────────


def test_login_user_chmod_cred_file_fails(tmp_path, monkeypatch):
    """login_user handles chmod failure on credentials file."""
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))

    from app.schemas.login import LoginRequest
    from app.services.login_service import login_user

    mock_user = {
        "idToken": "tok",
        "refreshToken": "ref",
        "localId": "u1",
    }
    mock_auth_client = MagicMock()
    mock_auth_client.sign_in_with_email_and_password.return_value = mock_user

    mock_firebase = MagicMock()
    mock_firebase.auth.return_value = (mock_auth_client, None)
    mock_firebase.register_user_tokens = MagicMock()

    call_count = [0]
    original_chmod = os.chmod

    def selective_chmod(path, mode):
        call_count[0] += 1
        if str(path).endswith("credentials.json"):
            raise OSError("chmod unsupported on file")
        return original_chmod(path, mode)

    mock_scheduler = MagicMock()

    with (
        patch("app.services.login_service.get_firebase", return_value=mock_firebase),
        patch("app.services.login_service.os.chmod", side_effect=selective_chmod),
        patch("app.services.login_service.scheduler", mock_scheduler),
    ):
        data = LoginRequest(email="user@example.com", password="pw")
        result = login_user(data)

    assert result.access_token == "tok"


# ── login_service – credentials file unlink exception (lines 152-153) ──────


def test_logout_user_unlink_exception(tmp_path, monkeypatch):
    """logout_user handles exception when removing credentials file."""
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))

    from app.services.login_service import logout_user

    user_id = "u_logout"
    user_dir = tmp_path / user_id
    user_dir.mkdir()
    cred_path = user_dir / "credentials.json"
    cred_path.write_text('{"idToken": "t"}')

    mock_firebase = MagicMock()
    mock_scheduler = MagicMock()

    Path.unlink

    def failing_unlink(self, missing_ok=False):
        raise OSError("cannot remove")

    with (
        patch("app.services.login_service.get_firebase", return_value=mock_firebase),
        patch("app.services.login_service.scheduler", mock_scheduler),
        patch.object(Path, "unlink", failing_unlink),
    ):
        result = logout_user(user_id)

    # Should still return True despite unlink failure
    assert result is True


# ── firebase_init – non-test environment paths (lines 41-66) ──────────────


def test_initialize_firebase_admin_no_credential_path(monkeypatch):
    """initialize_firebase_admin raises RuntimeError when no credentials path is set."""
    import app.core.firebase_init as fi_mod

    original_app = fi_mod._firebase_app
    monkeypatch.delenv("PYTEST_RUNNING", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("UNIT_TEST", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    fi_mod._firebase_app = None

    with patch("app.core.firebase_init.is_testing_env", return_value=False):
        with pytest.raises(RuntimeError, match="GOOGLE_APPLICATION_CREDENTIALS"):
            fi_mod.initialize_firebase_admin(force=True)

    fi_mod._firebase_app = original_app


def test_initialize_firebase_admin_invalid_credentials_file(tmp_path, monkeypatch):
    """initialize_firebase_admin raises when credentials file doesn't exist."""
    import app.core.firebase_init as fi_mod

    original_app = fi_mod._firebase_app
    fi_mod._firebase_app = None
    monkeypatch.setenv(
        "GOOGLE_APPLICATION_CREDENTIALS", str(tmp_path / "nonexistent.json")
    )

    with patch("app.core.firebase_init.is_testing_env", return_value=False):
        with pytest.raises(RuntimeError, match="GOOGLE_APPLICATION_CREDENTIALS"):
            fi_mod.initialize_firebase_admin(force=True)

    fi_mod._firebase_app = original_app


def test_initialize_firebase_admin_reuses_existing_app(monkeypatch):
    """initialize_firebase_admin returns cached app without re-initializing."""
    import app.core.firebase_init as fi_mod

    mock_app = MagicMock()
    original_app = fi_mod._firebase_app
    fi_mod._firebase_app = mock_app

    result = fi_mod.initialize_firebase_admin(force=False)
    assert result is mock_app

    fi_mod._firebase_app = original_app


def test_initialize_firebase_admin_reuses_firebase_admin_app(monkeypatch):
    """initialize_firebase_admin reuses existing firebase_admin app."""
    import firebase_admin

    import app.core.firebase_init as fi_mod

    original_app = fi_mod._firebase_app
    fi_mod._firebase_app = None

    existing_app = MagicMock(spec=firebase_admin.App)
    existing_app.credential = MagicMock()
    existing_app.credential.project_id = "reused-proj"

    with (
        patch("app.core.firebase_init.is_testing_env", return_value=False),
        patch.dict(
            "app.core.firebase_init.firebase_admin._apps", {"[DEFAULT]": existing_app}
        ),
        patch(
            "app.core.firebase_init.firebase_admin.get_app", return_value=existing_app
        ),
    ):
        result = fi_mod.initialize_firebase_admin(force=True)

    assert result is existing_app
    fi_mod._firebase_app = original_app


# ── get_project_id – force initialize path (lines 83-86) ─────────────────


def test_get_project_id_calls_initialize_when_not_cached():
    """get_project_id calls initialize_firebase_admin when _project_id not set."""
    import app.core.firebase_init as fi_mod

    original_project_id = fi_mod._project_id
    fi_mod._project_id = None  # force re-initialization

    with patch(
        "app.core.firebase_init.initialize_firebase_admin",
        side_effect=RuntimeError("Firebase not initialized; project_id unavailable"),
    ):
        with pytest.raises(RuntimeError, match="project_id unavailable"):
            fi_mod.get_project_id(allow_default=False)

    fi_mod._project_id = original_project_id
