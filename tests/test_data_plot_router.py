"""Tests for app.routers.data_plot – validation and error handling."""

import os
from unittest.mock import AsyncMock, patch

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user_id
from app.core.exceptions import (
    DeserializationDisabledError,
    DeserializationError,
)
from app.core.exceptions import FileNotFoundError as AppFileNotFoundError
from app.core.exceptions import (
    FileSizeExceededError,
)
from app.main import app


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user_id] = lambda: "plot_user"
    yield
    app.dependency_overrides.pop(get_current_user_id, None)


client = TestClient(app, raise_server_exceptions=False)


# ── _validate_user_id ──────────────────────────────────────────────────────


def test_list_invalid_user_id():
    """Invalid user_id format (e.g., path traversal) should return 400."""
    app.dependency_overrides[get_current_user_id] = lambda: "../evil"
    try:
        r = client.get("/data/list")
        assert r.status_code == 400
    finally:
        app.dependency_overrides[get_current_user_id] = lambda: "plot_user"


# ── _validate_filename ─────────────────────────────────────────────────────


def test_preview_invalid_filename_extension():
    r = client.get("/data/files/report.exe/preview")
    assert r.status_code == 400


def test_preview_filename_path_traversal():
    r = client.get("/data/files/evil!file.pkl/preview")
    assert r.status_code == 400


def test_series_invalid_filename():
    r = client.get("/data/files/bad.txt/series", params={"y": "col"})
    assert r.status_code == 400


# ── list_files – error handling ────────────────────────────────────────────


def test_list_files_success(tmp_path):
    os.environ["APP_USER_DATA_DIR"] = str(tmp_path)
    user_dir = tmp_path / "plot_user"
    user_dir.mkdir(parents=True)
    df = pd.DataFrame({"x": [1, 2]})
    df.to_pickle(user_dir / "data.pkl")
    r = client.get("/data/list")
    assert r.status_code == 200
    assert "files" in r.json()


def test_list_files_empty_dir(tmp_path):
    os.environ["APP_USER_DATA_DIR"] = str(tmp_path)
    (tmp_path / "plot_user").mkdir(parents=True)
    r = client.get("/data/list")
    assert r.status_code == 200
    assert r.json()["files"] == []


# ── preview_file – error handling ──────────────────────────────────────────


def test_preview_file_not_found():
    with patch(
        "app.routers.data_plot.data_service.preview_pickle_file_async",
        new_callable=AsyncMock,
        side_effect=AppFileNotFoundError("missing.pkl"),
    ):
        r = client.get("/data/files/missing.pkl/preview")
    assert r.status_code == 404


def test_preview_file_size_exceeded():
    with patch(
        "app.routers.data_plot.data_service.preview_pickle_file_async",
        new_callable=AsyncMock,
        side_effect=FileSizeExceededError(600, 500),
    ):
        r = client.get("/data/files/large.pkl/preview")
    assert r.status_code == 413


def test_preview_deserialization_disabled():
    with patch(
        "app.routers.data_plot.data_service.preview_pickle_file_async",
        new_callable=AsyncMock,
        side_effect=DeserializationDisabledError(),
    ):
        r = client.get("/data/files/secret.pkl/preview")
    assert r.status_code == 403


def test_preview_deserialization_error():
    with patch(
        "app.routers.data_plot.data_service.preview_pickle_file_async",
        new_callable=AsyncMock,
        side_effect=DeserializationError("broken.pkl", "bad magic"),
    ):
        r = client.get("/data/files/broken.pkl/preview")
    assert r.status_code == 400


def test_preview_unexpected_error():
    with patch(
        "app.routers.data_plot.data_service.preview_pickle_file_async",
        new_callable=AsyncMock,
        side_effect=RuntimeError("out of memory"),
    ):
        r = client.get("/data/files/oom.pkl/preview")
    assert r.status_code == 500


# ── get_series – error handling ────────────────────────────────────────────


def test_series_file_not_found():
    with patch(
        "app.routers.data_plot.data_service.extract_series_async",
        new_callable=AsyncMock,
        side_effect=AppFileNotFoundError("missing.pkl"),
    ):
        r = client.get("/data/files/missing.pkl/series", params={"y": "col"})
    assert r.status_code == 404


def test_series_file_size_exceeded():
    with patch(
        "app.routers.data_plot.data_service.extract_series_async",
        new_callable=AsyncMock,
        side_effect=FileSizeExceededError(700, 500),
    ):
        r = client.get("/data/files/big.pkl/series", params={"y": "val"})
    assert r.status_code == 413


def test_series_deserialization_disabled():
    with patch(
        "app.routers.data_plot.data_service.extract_series_async",
        new_callable=AsyncMock,
        side_effect=DeserializationDisabledError(),
    ):
        r = client.get("/data/files/secret.pkl/series", params={"y": "val"})
    assert r.status_code == 403


def test_series_deserialization_error():
    with patch(
        "app.routers.data_plot.data_service.extract_series_async",
        new_callable=AsyncMock,
        side_effect=DeserializationError("bad.pkl", "corrupt"),
    ):
        r = client.get("/data/files/bad.pkl/series", params={"y": "val"})
    assert r.status_code == 400


def test_series_value_error():
    with patch(
        "app.routers.data_plot.data_service.extract_series_async",
        new_callable=AsyncMock,
        side_effect=ValueError("no numeric column"),
    ):
        r = client.get("/data/files/data.pkl/series", params={"y": "missing"})
    assert r.status_code == 400


def test_series_unexpected_error():
    with patch(
        "app.routers.data_plot.data_service.extract_series_async",
        new_callable=AsyncMock,
        side_effect=RuntimeError("crash"),
    ):
        r = client.get("/data/files/data.pkl/series", params={"y": "val"})
    assert r.status_code == 500
