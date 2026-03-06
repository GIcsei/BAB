"""Tests for uncovered branches in auth, config, firebase_init, and router deps."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")
os.environ.setdefault("PYTEST_RUNNING", "1")

from app.core.auth import get_current_user_id, get_firebase_dep  # noqa: E402
from app.core.config import Settings, _to_int  # noqa: E402
from app.routers.login import get_scheduler_dep  # noqa: E402

# ── get_firebase_dep: firebase is None ────────────────────────────────────


def test_get_firebase_dep_returns_503_when_firebase_is_none():
    """get_firebase_dep raises 503 when Firebase is not initialized."""
    request = MagicMock()
    request.app.state.firebase = None

    with pytest.raises(HTTPException) as exc_info:
        get_firebase_dep(request)

    assert exc_info.value.status_code == 503
    assert "Firebase unavailable" in str(exc_info.value.detail)


def test_get_firebase_dep_returns_firebase_when_available():
    """get_firebase_dep returns Firebase instance when available."""
    mock_firebase = MagicMock()
    request = MagicMock()
    request.app.state.firebase = mock_firebase

    result = get_firebase_dep(request)
    assert result is mock_firebase


# ── get_current_user_id: empty token ──────────────────────────────────────


def test_get_current_user_id_raises_when_token_is_empty():
    """get_current_user_id raises 401 when credentials have empty token."""
    mock_fb = MagicMock()
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(creds=creds, firebase=mock_fb)

    assert exc_info.value.status_code == 401


# ── get_scheduler_dep: scheduler is None ──────────────────────────────────


def test_get_scheduler_dep_returns_503_when_scheduler_is_none():
    """get_scheduler_dep raises 503 when Scheduler is not initialized."""
    request = MagicMock()
    request.app.state.scheduler = None

    with pytest.raises(HTTPException) as exc_info:
        get_scheduler_dep(request)

    assert exc_info.value.status_code == 503
    assert "Scheduler unavailable" in str(exc_info.value.detail)


# ── _to_int: invalid value ────────────────────────────────────────────────


def test_to_int_returns_default_on_invalid_value():
    """_to_int returns the default when conversion fails."""
    result = _to_int("not_a_number", 42)
    assert result == 42


def test_to_int_returns_converted_value():
    """_to_int converts valid string to int."""
    result = _to_int("123", 0)
    assert result == 123


def test_to_int_returns_default_when_none():
    """_to_int returns default when value is None."""
    result = _to_int(None, 99)
    assert result == 99


# ── Settings validation ──────────────────────────────────────────────────


def test_settings_rejects_invalid_job_hour():
    """Settings raises ValueError for job_hour > 23."""
    with pytest.raises(ValueError, match="app_job_hour"):
        Settings(
            raw_app_user_data_dir=None,
            app_user_data_dir=Path("/tmp"),
            netbank_base_dir=Path("/tmp"),
            allow_unsafe_deserialize=False,
            app_job_hour=24,
            app_job_minute=0,
            google_application_credentials=None,
            log_level="INFO",
            log_file="",
            log_json=False,
            selenium_downloads_dir=None,
            local_downloads_dir=None,
            is_testing=True,
        )


def test_settings_rejects_negative_job_hour():
    """Settings raises ValueError for job_hour < 0."""
    with pytest.raises(ValueError, match="app_job_hour"):
        Settings(
            raw_app_user_data_dir=None,
            app_user_data_dir=Path("/tmp"),
            netbank_base_dir=Path("/tmp"),
            allow_unsafe_deserialize=False,
            app_job_hour=-1,
            app_job_minute=0,
            google_application_credentials=None,
            log_level="INFO",
            log_file="",
            log_json=False,
            selenium_downloads_dir=None,
            local_downloads_dir=None,
            is_testing=True,
        )


def test_settings_rejects_invalid_job_minute():
    """Settings raises ValueError for job_minute > 59."""
    with pytest.raises(ValueError, match="app_job_minute"):
        Settings(
            raw_app_user_data_dir=None,
            app_user_data_dir=Path("/tmp"),
            netbank_base_dir=Path("/tmp"),
            allow_unsafe_deserialize=False,
            app_job_hour=12,
            app_job_minute=60,
            google_application_credentials=None,
            log_level="INFO",
            log_file="",
            log_json=False,
            selenium_downloads_dir=None,
            local_downloads_dir=None,
            is_testing=True,
        )


# ── firebase_init: get_project_id branches ───────────────────────────────


def test_get_project_id_raises_when_not_initialized():
    """get_project_id raises RuntimeError when Firebase not initialized and no allow_default."""
    with patch("app.core.firebase_init._project_id", None):
        with patch(
            "app.core.firebase_init.initialize_firebase_admin", return_value=None
        ):
            from app.core.firebase_init import get_project_id

            with pytest.raises(RuntimeError, match="project_id unavailable"):
                get_project_id(allow_default=False)


def test_get_project_id_after_init_sets_project_id():
    """get_project_id returns the project_id after initialize_firebase_admin sets it."""
    with patch("app.core.firebase_init._project_id", "my-project"):
        from app.core.firebase_init import get_project_id

        result = get_project_id()
        assert result == "my-project"


# ── firebase_init: get_credential branches ────────────────────────────────


def test_get_credential_as_dict_reads_json(tmp_path: Path):
    """get_credential with as_dict=True reads JSON from file."""
    cred_file = tmp_path / "creds.json"
    cred_data = {"project_id": "test", "type": "service_account"}
    cred_file.write_text(json.dumps(cred_data))

    with patch("app.core.firebase_init.is_testing_env", return_value=False):
        mock_settings = MagicMock()
        mock_settings.google_application_credentials = cred_file
        with patch("app.core.firebase_init.get_settings", return_value=mock_settings):
            from app.core.firebase_init import get_credential

            result = get_credential(as_dict=True)
            assert result == cred_data


def test_get_credential_raises_when_file_missing():
    """get_credential raises RuntimeError when credentials file doesn't exist."""
    with patch("app.core.firebase_init.is_testing_env", return_value=False):
        mock_settings = MagicMock()
        mock_settings.google_application_credentials = Path("/nonexistent/creds.json")
        with patch("app.core.firebase_init.get_settings", return_value=mock_settings):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
                from app.core.firebase_init import get_credential

                with pytest.raises(
                    RuntimeError, match="GOOGLE_APPLICATION_CREDENTIALS"
                ):
                    get_credential()


def test_get_credential_uses_fallback_env_var(tmp_path: Path):
    """get_credential uses GOOGLE_APPLICATION_CREDENTIALS env var as fallback."""
    cred_file = tmp_path / "fallback.json"
    cred_data = {"project_id": "fallback-test"}
    cred_file.write_text(json.dumps(cred_data))

    with patch("app.core.firebase_init.is_testing_env", return_value=False):
        mock_settings = MagicMock()
        mock_settings.google_application_credentials = None
        with patch("app.core.firebase_init.get_settings", return_value=mock_settings):
            with patch.dict(
                os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": str(cred_file)}
            ):
                from app.core.firebase_init import get_credential

                result = get_credential(as_dict=True)
                assert result == cred_data
