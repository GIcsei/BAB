from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from app.core.auth import get_current_user_id
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def setup_app_state(monkeypatch):
    monkeypatch.setenv("PYTEST_RUNNING", "1")
    app.state.scheduler = None
    app.state.firebase = None
    yield
    app.dependency_overrides.clear()


def test_list_endpoint_and_preview_and_series(tmp_path: Path):
    base = tmp_path / "userdata"
    user = base / "alice"
    user.mkdir(parents=True)
    df = pd.DataFrame(
        {"date": pd.date_range("2020-01-01", periods=3), "val": [10, 20, 30]}
    )
    df.to_parquet(user / "d.parquet")

    app.dependency_overrides[get_current_user_id] = lambda: "alice"

    client = TestClient(app)

    try:
        with patch("app.routers.data_plot._base_dir", return_value=base):
            r = client.get("/data/list")
            assert r.status_code == 200
            assert "files" in r.json()

            r = client.get("/data/files/d.parquet/preview")
            assert r.status_code == 200
            assert "preview" in r.json()

            r = client.get("/data/files/d.parquet/series", params={"y": "val"})
            assert r.status_code == 200
            data = r.json()
            assert "x" in data and "y" in data
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)
