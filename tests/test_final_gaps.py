"""Tests for remaining small coverage gaps."""
import os
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest


# ── credentials – _ensure_config_dir chmod failure (lines 35-36) ─────────


def test_ensure_config_dir_chmod_failure(tmp_path):
    """_ensure_config_dir handles chmod failure gracefully."""
    from app.core.netbank.credentials import _ensure_config_dir

    config_dir = str(tmp_path / "netbank")

    with patch("app.core.netbank.credentials.os.chmod", side_effect=OSError("not supported")):
        # Should not raise
        _ensure_config_dir(config_dir)

    # Directory should still be created
    assert os.path.isdir(config_dir)


# ── firebase_init – get_project_id returns cached _project_id ─────────────


def test_get_project_id_returns_cached_project_id():
    """get_project_id returns cached _project_id if already set."""
    import app.core.firebase_init as fi_mod

    original = fi_mod._project_id
    fi_mod._project_id = "cached-project-id"

    result = fi_mod.get_project_id()
    assert result == "cached-project-id"

    fi_mod._project_id = original


# ── scheduler – inner firebase exception (lines 120-121) ─────────────────


def test_perform_task_inner_firebase_exception(tmp_path):
    """_perform_task handles inner exception (both set_active_user and load fail)."""
    from app.services.scheduler import _Job

    mock_broker = MagicMock()
    mock_broker.get_report.return_value = None

    fake_mod = ModuleType("app.core.netbank.getReport")
    fake_mod.ErsteNetBroker = MagicMock(return_value=mock_broker)

    mock_firebase = MagicMock()
    # First call to set_active_user raises, then load_tokens_from_dir raises too
    mock_firebase.set_active_user.side_effect = ValueError("no token")
    mock_firebase.load_tokens_from_dir.side_effect = ValueError("load fails")
    # Both fail -> inner exception at lines 115-121

    with (
        patch("app.services.login_service.firebase", mock_firebase),
        patch.dict("sys.modules", {"app.core.netbank.getReport": fake_mod}),
    ):
        job = _Job("u1", tmp_path)
        job._perform_task()  # should not raise despite inner exception

    mock_broker.get_report.assert_called_once()

