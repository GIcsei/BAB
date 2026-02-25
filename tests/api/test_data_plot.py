import os
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_user_id


@pytest.fixture(autouse=True)
def setup_app_state(monkeypatch):
    monkeypatch.setenv("PYTEST_RUNNING", "1")
    app.state.scheduler = None
    app.state.firebase = None
    yield
    app.dependency_overrides.clear()


def test_list_endpoint_and_preview_and_series(tmp_path: Path):
    base = tmp_path / "userdata"
    os.environ["APP_USER_DATA_DIR"] = str(base)
    user = base / "alice"
    user.mkdir(parents=True)
    df = pd.DataFrame(
        {"date": pd.date_range("2020-01-01", periods=3), "val": [10, 20, 30]}
    )
    pkl = user / "d.pkl"
    df.to_pickle(pkl)

    app.dependency_overrides[get_current_user_id] = lambda: "alice"

    client = TestClient(app)

    try:
        r = client.get("/data/list")
        assert r.status_code == 200
        assert "files" in r.json()

        r = client.get("/data/files/d.pkl/preview")
        assert r.status_code == 200
        assert "preview" in r.json()

        r = client.get("/data/files/d.pkl/series", params={"y": "val"})
        assert r.status_code == 200
        data = r.json()
        assert "x" in data and "y" in data
    finally:
        app.dependency_overrides.pop(get_current_user_id, None)
