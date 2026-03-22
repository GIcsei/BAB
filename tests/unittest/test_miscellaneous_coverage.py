"""Additional data_service and router tests for coverage gaps."""

import os
import pickle
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

import pandas as pd
import pytest
from app.services import data_service
from app.services.data_service import (
    _to_json_serializable,
    _validate_file_size,
    list_pickles_for_user,
)

# ── _validate_file_size – app FileNotFoundError catch (lines 46-48) ──────


def test_validate_file_size_catches_app_file_not_found_error(tmp_path):
    """_validate_file_size raises AppFileNotFoundError when caught via app exception."""
    from app.core.exceptions import FileNotFoundError as AppFNFError

    with patch(
        "app.services.data_service.Path.stat",
        side_effect=AppFNFError("not found"),
    ):
        with pytest.raises(AppFNFError):
            _validate_file_size(tmp_path / "file.pkl")


# ── list_pickles_for_user – file stat error (lines 67-68) ─────────────────


def test_list_pickles_stat_error(tmp_path):
    """list_pickles_for_user skips files that can't be stat'd."""
    user_dir = tmp_path / "u1"
    user_dir.mkdir()
    pkl_file = user_dir / "data.pkl"
    pkl_file.write_bytes(pickle.dumps([1, 2, 3]))

    original_stat = Path.stat

    def failing_stat(self, **kwargs):
        if self.suffix == ".pkl":
            raise OSError("perm denied")
        return original_stat(self, **kwargs)

    with patch.object(Path, "stat", failing_stat):
        result = list_pickles_for_user(tmp_path, "u1")

    # The exception is caught and the file is skipped
    assert result == []


# ── list_pickles_for_user – directory listing error (lines 69-70) ──────────


def test_list_pickles_iterdir_error(tmp_path):
    """list_pickles_for_user handles error when listing directory."""
    user_dir = tmp_path / "u1"
    user_dir.mkdir()

    with patch.object(Path, "iterdir", side_effect=OSError("cannot list")):
        result = list_pickles_for_user(tmp_path, "u1")

    assert result == []


# ── _try_load – joblib success path (lines 93-96) ─────────────────────────


def test_try_load_all_fail_raises_deserialization_error(tmp_path):
    """_try_load raises DeserializationError when all methods fail."""
    from app.core.exceptions import DeserializationError

    path = tmp_path / "bad.pkl"
    path.write_bytes(b"not a valid pickle file at all xyz")

    with pytest.raises(DeserializationError):
        data_service._try_load(path)


# ── _to_json_serializable – conv_item exception path (lines 161-162) ─────


def test_to_json_serializable_list_with_str_exception():
    """_to_json_serializable handles items whose str() raises."""

    class BadRepr:
        def __str__(self):
            raise RuntimeError("no str")

    lst = [BadRepr(), 42, "hello"]
    result = _to_json_serializable(lst)
    # The BadRepr item becomes None
    assert result["type"] == "list"
    assert result["sample"][0] is None
    assert result["sample"][1] == 42


# ── _to_json_serializable – conversion exception (lines 184-186) ─────────


def test_to_json_serializable_exception_returns_error():
    """_to_json_serializable returns error dict when conversion raises."""

    class Explosive:
        def __class_getitem__(cls, item):
            raise RuntimeError()

    # Patch isinstance to raise during conversion
    with patch(
        "app.services.data_service.isinstance", side_effect=RuntimeError("boom")
    ):
        result = _to_json_serializable([1, 2, 3])

    assert result["type"] == "error"


# ── preview_pickle_file_async (line 196) ─────────────────────────────────


def test_preview_pickle_file_async(tmp_path):
    """preview_pickle_file_async wraps preview_pickle_file in a thread."""
    import asyncio

    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"x": [1, 2, 3]})
    (user / "df.pkl").write_bytes(pickle.dumps(df))

    result = asyncio.get_event_loop().run_until_complete(
        data_service.preview_pickle_file_async(base, "u1", "df.pkl")
    )
    assert result["type"] == "dataframe"


# ── extract_series_async (line 233) ──────────────────────────────────────


def test_extract_series_async(tmp_path):
    """extract_series_async wraps extract_series in a thread."""
    import asyncio

    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"val": [1.0, 2.0, 3.0]})
    (user / "df.pkl").write_bytes(pickle.dumps(df))

    result = asyncio.get_event_loop().run_until_complete(
        data_service.extract_series_async(
            base, "u1", "df.pkl", x_column=None, y_column="val"
        )
    )
    assert "y" in result


# ── routers/data_plot.py lines 53-55 (list_files error handling) ──────────


def test_list_files_exception_returns_500():
    """list_files should return 500 for unexpected errors."""
    from app.core.auth import get_current_user_id
    from app.main import app
    from fastapi.testclient import TestClient

    app.dependency_overrides[get_current_user_id] = lambda: "u1"
    client = TestClient(app, raise_server_exceptions=False)

    with patch(
        "app.routers.data_plot.data_service.list_data_files_for_user",
        side_effect=OSError("disk error"),
    ):
        r = client.get("/data/list")
    assert r.status_code == 500

    app.dependency_overrides.pop(get_current_user_id, None)


# ── routers/login.py lines 25-26 (ValidationError handler) ──────────────


def test_login_validation_error_returns_422():
    """Login with invalid email format returns 422."""
    from app.core.auth import get_firebase_dep
    from app.main import app
    from app.routers.login import get_scheduler_dep
    from fastapi.testclient import TestClient

    app.dependency_overrides[get_firebase_dep] = lambda: MagicMock()
    app.dependency_overrides[get_scheduler_dep] = lambda: MagicMock()
    client = TestClient(app, raise_server_exceptions=False)
    try:
        r = client.post("/user/login", json={"email": "not-an-email", "password": "pw"})
        assert r.status_code == 422
    finally:
        app.dependency_overrides.pop(get_firebase_dep, None)
        app.dependency_overrides.pop(get_scheduler_dep, None)


# ── routers/login.py lines 79-81 (logout exception) ─────────────────────


def test_logout_exception_returns_500():
    """logout route returns 500 when logout_user raises an unexpected error."""
    from app.core.auth import get_current_user_id, get_firebase_dep
    from app.main import app
    from app.routers.login import get_scheduler_dep
    from fastapi.testclient import TestClient

    app.dependency_overrides[get_current_user_id] = lambda: "u1"
    app.dependency_overrides[get_firebase_dep] = lambda: MagicMock()
    app.dependency_overrides[get_scheduler_dep] = lambda: MagicMock()
    client = TestClient(app, raise_server_exceptions=False)

    try:
        with patch(
            "app.routers.login.logout_user", side_effect=RuntimeError("unexpected")
        ):
            r = client.post("/user/logout")
        assert r.status_code in (500, 502)
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)
        app.dependency_overrides.pop(get_firebase_dep, None)
        app.dependency_overrides.pop(get_scheduler_dep, None)


# ── login_service – firebase singleton line 21 ────────────────────────────


def test_login_service_has_login_user_function():
    """login_service module exports login_user function."""
    import app.services.login_service as ls

    assert hasattr(ls, "login_user")
    assert callable(ls.login_user)
