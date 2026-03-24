import os
from pathlib import Path

import pandas as pd

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

from app.services import data_service  # noqa: E402


def test_list_pickles_for_user_empty(tmp_path: Path):
    base = tmp_path / "data"
    base.mkdir()
    files = data_service.list_pickles_for_user(base, "missing_user")
    assert files == []


def test_list_data_files_for_user_filters_extensions(tmp_path: Path):
    base = tmp_path / "data"
    user = base / "user1"
    user.mkdir(parents=True)
    (user / "a.txt").write_text("ignore")
    df = pd.DataFrame({"x": [1, 2, 3]})
    df.to_parquet(user / "sample.parquet")
    result = data_service.list_data_files_for_user(base, "user1")
    assert any(f["filename"] == "sample.parquet" for f in result)


def test_preview_data_file_dataframe(tmp_path: Path):
    base = tmp_path / "data"
    user = base / "user2"
    user.mkdir(parents=True)
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    df.to_parquet(user / "df.parquet")

    preview = data_service.preview_pickle_file(base, "user2", "df.parquet", max_rows=2)
    assert isinstance(preview, dict)
    assert preview.get("type") == "dataframe"


def test_extract_series_dataframe_datetime_index(tmp_path: Path):
    base = tmp_path / "data"
    user = base / "user3"
    user.mkdir(parents=True)
    dates = pd.date_range("2021-01-01", periods=5, freq="D")
    df = pd.DataFrame({"value": [1, 2, 3, 4, 5]}, index=dates)
    df.to_parquet(user / "series.parquet")

    res = data_service.extract_series(
        base,
        "user3",
        "series.parquet",
        x_column=None,
        y_column="value",
        max_points=10,
    )
    assert "x" in res and "y" in res
    assert len(res["x"]) == len(res["y"]) == 5


def test_extract_series_csv(tmp_path: Path):
    base = tmp_path / "data"
    user = base / "user4"
    user.mkdir(parents=True)
    df = pd.DataFrame({"val": [0.1, 0.2, 0.3]})
    df.to_csv(user / "arr.csv", index=False)
    res = data_service.extract_series(
        base, "user4", "arr.csv", x_column=None, y_column="val", max_points=10
    )
    assert isinstance(res["y"], list)
