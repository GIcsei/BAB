"""Extended tests for app.services.data_service – more branches and types."""

import os

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

from app.core.exceptions import (
    FileNotFoundError,
    FileSizeExceededError,
)
from app.services import data_service
from app.services.data_service import (
    _to_json_serializable,
    _validate_file_size,
    extract_series,
    preview_pickle_file,
)

# ── _validate_file_size ────────────────────────────────────────────────────


def test_validate_file_size_ok(tmp_path):
    f = tmp_path / "small.parquet"
    f.write_bytes(b"x" * 100)
    # should not raise
    _validate_file_size(f)


def test_validate_file_size_exceeds_limit(tmp_path):
    f = tmp_path / "large.parquet"
    # write just over 1 MB
    f.write_bytes(b"x" * (1 * 1024 * 1024 + 1))
    with pytest.raises(FileSizeExceededError):
        _validate_file_size(f, max_size_mb=1)


def test_validate_file_size_nonexistent(tmp_path):
    f = tmp_path / "missing.parquet"
    # path.stat() raises OSError which is caught and re-raised as the custom
    # app.core.exceptions.FileNotFoundError
    with pytest.raises(FileNotFoundError):
        _validate_file_size(f)


# ── _to_json_serializable ──────────────────────────────────────────────────


def test_to_json_serializable_dataframe():
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    result = _to_json_serializable(df)
    assert result["type"] == "dataframe"
    assert "columns" in result
    assert "rows" in result
    assert result["n_rows"] == 3


def test_to_json_serializable_dataframe_truncated():
    df = pd.DataFrame({"v": range(300)})
    result = _to_json_serializable(df, max_rows=10)
    assert result["type"] == "dataframe"
    assert len(result["rows"]) == 10


def test_to_json_serializable_series():
    s = pd.Series([1.0, 2.0, 3.0], name="myseries")
    result = _to_json_serializable(s)
    assert result["type"] == "series"
    assert "values" in result
    assert "index" in result
    assert result["n_rows"] == 3


def test_to_json_serializable_ndarray():
    arr = np.array([[1, 2], [3, 4]])
    result = _to_json_serializable(arr)
    assert result["type"] == "ndarray"
    assert result["shape"] == (2, 2)
    assert "values" in result


def test_to_json_serializable_list():
    lst = [1, 2, 3, "hello", None]
    result = _to_json_serializable(lst)
    assert result["type"] == "list"
    assert result["length"] == 5
    assert "sample" in result


def test_to_json_serializable_list_with_complex_items():
    lst = [{"nested": True}, [1, 2], object()]
    result = _to_json_serializable(lst)
    assert result["type"] == "list"


def test_to_json_serializable_dict():
    d = {"name": "alice", "score": 42, "active": True}
    result = _to_json_serializable(d)
    assert result["type"] == "dict"
    assert "sample_keys" in result
    assert "name" in result["sample_keys"]


def test_to_json_serializable_dict_with_complex_values():
    d = {"df": pd.DataFrame({"x": [1]}), "simple": "ok"}
    result = _to_json_serializable(d)
    assert result["type"] == "dict"


def test_to_json_serializable_unknown_type():
    class Custom:
        pass

    result = _to_json_serializable(Custom())
    assert result["type"] == "unknown"
    assert "repr" in result


# ── preview_pickle_file ────────────────────────────────────────────────────


def test_preview_parquet_series(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    s = pd.Series([10.0, 20.0, 30.0])
    pd.DataFrame({"value": s}).to_parquet(user / "series.parquet")
    result = preview_pickle_file(base, "u1", "series.parquet")
    assert result["type"] == "dataframe"


def test_preview_parquet_dataframe(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"a": [1, 2, 3, 4, 5]})
    df.to_parquet(user / "arr.parquet")
    result = preview_pickle_file(base, "u1", "arr.parquet")
    assert result["type"] == "dataframe"


def test_preview_csv_list(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    pd.DataFrame({"x": [1, 2, 3]}).to_csv(user / "lst.csv", index=False)
    result = preview_pickle_file(base, "u1", "lst.csv")
    assert result["type"] == "dataframe"


def test_preview_file_not_found_raises(tmp_path):
    base = tmp_path / "data"
    base.mkdir()
    (base / "u1").mkdir()
    # _validate_file_size catches OSError and re-raises as custom FileNotFoundError
    with pytest.raises(FileNotFoundError):
        preview_pickle_file(base, "u1", "missing.parquet")


# ── extract_series – more branches ────────────────────────────────────────


def test_extract_series_dataframe_with_explicit_x_column(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"ts": ["2020-01", "2020-02", "2020-03"], "val": [1, 2, 3]})
    df.to_parquet(user / "df.parquet")
    res = extract_series(base, "u1", "df.parquet", x_column="ts", y_column="val")
    assert res["x"] == ["2020-01", "2020-02", "2020-03"]
    assert res["y"] == [1.0, 2.0, 3.0]


def test_extract_series_dataframe_auto_pick_y_column(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"label": ["a", "b"], "amount": [100.0, 200.0]})
    df.to_parquet(user / "df.parquet")
    # y_column 'missing' is not in df, auto-picks numeric
    res = extract_series(base, "u1", "df.parquet", x_column=None, y_column="missing")
    assert "y" in res
    assert len(res["y"]) == 2


def test_extract_series_dataframe_date_column(tmp_path):
    """When no x_column and no datetime index, fall back to 'date' column."""
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"date": ["2020-01-01", "2020-01-02"], "val": [5, 6]})
    df.to_parquet(user / "df.parquet")
    res = extract_series(base, "u1", "df.parquet", x_column=None, y_column="val")
    assert "x" in res


def test_extract_series_dataframe_no_numeric_column_raises(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"label": ["a", "b"], "name": ["x", "y"]})
    df.to_parquet(user / "df.parquet")
    with pytest.raises(ValueError, match="No numeric column"):
        extract_series(base, "u1", "df.parquet", x_column=None, y_column="missing")


def test_extract_series_dataframe_missing_x_column_uses_index(tmp_path):
    """x_column specified but not found – fall back to datetime index."""
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    dates = pd.date_range("2021-01-01", periods=3, freq="D")
    df = pd.DataFrame({"val": [1, 2, 3]}, index=dates)
    df.to_parquet(user / "df.parquet")
    res = extract_series(
        base, "u1", "df.parquet", x_column="nonexistent", y_column="val"
    )
    assert len(res["x"]) == 3


def test_extract_series_dataframe_range_index_fallback(tmp_path):
    """x_column specified but not found, and index is not datetime -> use range."""
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"val": [1, 2, 3]})
    df.to_parquet(user / "df.parquet")
    res = extract_series(base, "u1", "df.parquet", x_column="noexist", y_column="val")
    assert res["x"] == ["0", "1", "2"]


def test_extract_series_csv(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"price": [10.0, 20.0, 30.0]})
    df.to_csv(user / "s.csv", index=False)
    res = extract_series(base, "u1", "s.csv", x_column=None, y_column="price")
    assert len(res["y"]) == 3


def test_extract_series_max_points_trim(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"val": range(100)})
    df.to_parquet(user / "df.parquet")
    res = extract_series(
        base, "u1", "df.parquet", x_column=None, y_column="val", max_points=10
    )
    assert len(res["y"]) == 10


def test_list_data_files_sorts_by_name(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    for name in ["c.csv", "a.csv", "b.csv"]:
        pd.DataFrame({"x": [1]}).to_csv(user / name, index=False)
    result = data_service.list_data_files_for_user(base, "u1")
    names = [f["filename"] for f in result]
    assert names == sorted(names)


def test_list_data_files_includes_parquet(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    pd.DataFrame({"x": [1]}).to_parquet(user / "data.parquet")
    result = data_service.list_data_files_for_user(base, "u1")
    assert any(f["filename"] == "data.parquet" for f in result)
