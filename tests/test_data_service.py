import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from app.services import data_service

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")


def test_list_pickles_for_user_empty(tmp_path: Path):
    base = tmp_path / "data"
    base.mkdir()
    files = data_service.list_pickles_for_user(base, "missing_user")
    assert files == []


def test_list_pickles_for_user_filters_extensions(tmp_path: Path):
    base = tmp_path / "data"
    user = base / "user1"
    user.mkdir(parents=True)
    (user / "a.txt").write_text("ignore")
    df = pd.DataFrame({"x": [1, 2, 3]})
    pkl = user / "sample.pkl"
    df.to_pickle(pkl)
    result = data_service.list_pickles_for_user(base, "user1")
    assert any(f["filename"] == "sample.pkl" for f in result)


def test_preview_pickle_file_dataframe(tmp_path: Path):
    base = tmp_path / "data"
    user = base / "user2"
    user.mkdir(parents=True)
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    pkl = user / "df.pkl"
    df.to_pickle(pkl)

    preview = data_service.preview_pickle_file(base, "user2", "df.pkl", max_rows=2)
    assert isinstance(preview, dict)
    assert (
        preview.get("type") == "dataframe"
        or preview.get("type") is None
        and "rows" in preview
    )


def test_extract_series_dataframe_datetime_index(tmp_path: Path):
    base = tmp_path / "data"
    user = base / "user3"
    user.mkdir(parents=True)
    dates = pd.date_range("2021-01-01", periods=5, freq="D")
    df = pd.DataFrame({"value": [1, 2, 3, 4, 5]}, index=dates)
    pkl = user / "series.pkl"
    df.to_pickle(pkl)

    res = data_service.extract_series(
        base, "user3", "series.pkl", x_column=None, y_column="value", max_points=10
    )
    assert "x" in res and "y" in res
    assert len(res["x"]) == len(res["y"]) == 5


def test_extract_series_list_and_ndarray(tmp_path: Path):
    base = tmp_path / "data"
    user = base / "user4"
    user.mkdir(parents=True)
    arr = np.array([0.1, 0.2, 0.3])
    (user / "arr.pkl").write_bytes(pickle.dumps(arr))
    res = data_service.extract_series(
        base, "user4", "arr.pkl", x_column=None, y_column="unused", max_points=10
    )
    assert res["meta"]["shape"] == arr.shape or isinstance(res["y"], list)
