import os
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import app.main as main_mod
from app.main import app


@pytest.fixture(autouse=True)
def disable_startup(monkeypatch):
    # prevent startup code from attempting real scheduler/firebase work during tests
    if hasattr(main_mod, "scheduler"):
        monkeypatch.setattr(main_mod.scheduler, "restore_jobs_from_dir", lambda *a, **k: None)
    if hasattr(main_mod, "firebase"):
        monkeypatch.setattr(main_mod.firebase, "load_tokens_from_dir", lambda *a, **k: None)
    yield


def test_list_endpoint_and_preview_and_series(tmp_path: Path):
    # prepare env and sample data
    base = tmp_path / "userdata"
    os.environ["APP_USER_DATA_DIR"] = str(base)
    user = base / "alice"
    user.mkdir(parents=True)
    df = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=3), "val": [10, 20, 30]})
    pkl = user / "d.pkl"
    df.to_pickle(pkl)

    client = TestClient(app)

    # list
    r = client.get("/data/list", params={"user_id": "alice"})
    assert r.status_code == 200
    assert "files" in r.json()

    # preview
    r = client.get("/data/alice/files/d.pkl/preview")
    assert r.status_code == 200
    assert "preview" in r.json()

    # series (use y=val)
    r = client.get("/data/alice/files/d.pkl/series", params={"y": "val"})
    assert r.status_code == 200
    data = r.json()
    assert "x" in data and "y" in data