"""Final coverage tests for data_service, firebase_init, credentials, login_service."""
import json
import os
import pickle
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
import pandas as pd

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

from app.services import data_service


# ── data_service – joblib fallback (lines 93-97) ──────────────────────────


def test_try_load_joblib_fails_falls_back_to_pandas(tmp_path):
    """_try_load tries joblib first (fails), then falls back to pandas.read_pickle."""
    df = pd.DataFrame({"a": [1, 2, 3]})
    path = tmp_path / "df.pkl"
    path.write_bytes(pickle.dumps(df))

    # Create a fake joblib module that fails on load
    fake_joblib = ModuleType("joblib")
    fake_joblib.load = MagicMock(side_effect=ValueError("joblib cannot load this"))

    with patch.dict("sys.modules", {"joblib": fake_joblib}):
        # Also reload the data_service module to pick up the patched joblib
        result = data_service._try_load(path)

    assert isinstance(result, pd.DataFrame)


# ── firebase_init – get project_id from credential raises (lines 48-52) ───


def test_initialize_firebase_admin_get_project_id_from_cred_raises(monkeypatch):
    """initialize_firebase_admin handles exception when getting project_id from credential."""
    import app.core.firebase_init as fi_mod

    original_app = fi_mod._firebase_app
    original_pid = fi_mod._project_id
    fi_mod._firebase_app = None
    fi_mod._project_id = None

    mock_existing_app = MagicMock()
    mock_cred = MagicMock()
    # Make project_id raise a non-AttributeError (so getattr won't suppress it)
    type(mock_cred).project_id = PropertyMock(side_effect=RuntimeError("cred broken"))
    mock_existing_app.credential = mock_cred

    with (
        patch("app.core.firebase_init.is_testing_env", return_value=False),
        patch.dict("app.core.firebase_init.firebase_admin._apps", {"[DEFAULT]": mock_existing_app}),
        patch("app.core.firebase_init.firebase_admin.get_app", return_value=mock_existing_app),
    ):
        result = fi_mod.initialize_firebase_admin(force=True)

    assert result is mock_existing_app
    assert fi_mod._project_id is None  # exception caught, project_id is None

    fi_mod._firebase_app = original_app
    fi_mod._project_id = original_pid


# ── firebase_init – initialize with service account file (lines 62-66) ───


def test_initialize_firebase_admin_with_service_account(tmp_path, monkeypatch):
    """initialize_firebase_admin initializes with a service account JSON file."""
    import app.core.firebase_init as fi_mod

    original_app = fi_mod._firebase_app
    original_pid = fi_mod._project_id
    fi_mod._firebase_app = None
    fi_mod._project_id = None

    # Create a fake service account JSON
    sa_file = tmp_path / "service_account.json"
    sa_data = {
        "type": "service_account",
        "project_id": "my-test-proj",
        "private_key_id": "key1",
        "private_key": "fake_key",
        "client_email": "test@my-test-proj.iam.gserviceaccount.com",
        "client_id": "123",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    sa_file.write_text(json.dumps(sa_data))
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(sa_file))

    mock_cred = MagicMock()
    mock_cred.project_id = "my-test-proj"
    mock_new_app = MagicMock()

    with (
        patch("app.core.firebase_init.is_testing_env", return_value=False),
        patch.dict("app.core.firebase_init.firebase_admin._apps", {}),
        patch("app.core.firebase_init.credentials.Certificate", return_value=mock_cred),
        patch("app.core.firebase_init.firebase_admin.initialize_app", return_value=mock_new_app),
    ):
        result = fi_mod.initialize_firebase_admin(force=True)

    assert result is mock_new_app
    assert fi_mod._project_id == "my-test-proj"

    fi_mod._firebase_app = original_app
    fi_mod._project_id = original_pid


# ── login_service – _FirebaseAccessor.__getattr__ (line 21) ───────────────


def test_firebase_accessor_getattr():
    """_FirebaseAccessor.__getattr__ delegates attribute access to get_firebase()."""
    import app.services.login_service as ls

    mock_fb = MagicMock()
    mock_fb.some_attribute = "test_value"

    with patch("app.services.login_service.get_firebase", return_value=mock_fb):
        # Access attribute through the firebase accessor (line 21 is called here)
        result = ls.firebase.some_attribute

    assert result == "test_value"


# ── credentials – _ensure_key all writes fail (lines 91-93) ──────────────


def test_ensure_key_all_writes_fail(tmp_path, monkeypatch):
    """_ensure_key raises when both fdopen and open fail."""
    monkeypatch.delenv("NETBANK_MASTER_KEY", raising=False)

    with (
        patch("app.core.netbank.credentials.os.fdopen", side_effect=OSError("fdopen fail")),
        patch("builtins.open", side_effect=OSError("open fail")),
    ):
        with pytest.raises(OSError):
            from app.core.netbank.credentials import _ensure_key
            _ensure_key(str(tmp_path))


# ── credentials – save_user_credentials all writes fail (lines 145-147) ───


def test_save_user_credentials_all_writes_fail(tmp_path, monkeypatch):
    """save_user_credentials raises when both fdopen and open fail during write."""
    original_fdopen = os.fdopen

    def failing_fdopen(fd, *args, **kwargs):
        # Fail all text-mode writes (for the credential file)
        mode = args[0] if args else kwargs.get("mode", "")
        if "w" in mode and "b" not in mode:
            os.close(fd)
            raise OSError("fdopen write fail")
        return original_fdopen(fd, *args, **kwargs)

    with (
        patch("app.core.netbank.credentials.os.fdopen", side_effect=failing_fdopen),
        patch("app.core.netbank.credentials.open", side_effect=OSError("open write fail")),
    ):
        with pytest.raises(OSError):
            from app.core.netbank.credentials import save_user_credentials
            save_user_credentials("u1", "user", "ACC", "pw", config_dir=str(tmp_path))
