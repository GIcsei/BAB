"""Extended tests for app.services.data_service – more branches and types."""

import os
import pickle

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

from app.core.exceptions import (
    DeserializationDisabledError,
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
    f = tmp_path / "small.pkl"
    f.write_bytes(b"x" * 100)
    # should not raise
    _validate_file_size(f)


def test_validate_file_size_exceeds_limit(tmp_path):
    f = tmp_path / "large.pkl"
    # write just over 1 MB
    f.write_bytes(b"x" * (1 * 1024 * 1024 + 1))
    with pytest.raises(FileSizeExceededError):
        _validate_file_size(f, max_size_mb=1)


def test_validate_file_size_nonexistent(tmp_path):
    f = tmp_path / "missing.pkl"
    # path.stat() raises the built-in FileNotFoundError (OSError);
    # the custom except only catches app.core.exceptions.FileNotFoundError,
    # so the built-in OSError propagates
    with pytest.raises(OSError):
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


def test_preview_pickle_series(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    s = pd.Series([10.0, 20.0, 30.0])
    (user / "series.pkl").write_bytes(pickle.dumps(s))
    result = preview_pickle_file(base, "u1", "series.pkl")
    assert result["type"] == "series"


def test_preview_pickle_ndarray(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    arr = np.array([1, 2, 3, 4, 5])
    (user / "arr.pkl").write_bytes(pickle.dumps(arr))
    result = preview_pickle_file(base, "u1", "arr.pkl")
    assert result["type"] == "ndarray"


def test_preview_pickle_list(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    lst = [1, 2, 3]
    (user / "lst.pkl").write_bytes(pickle.dumps(lst))
    result = preview_pickle_file(base, "u1", "lst.pkl")
    assert result["type"] == "list"


def test_preview_file_not_found_raises(tmp_path):
    base = tmp_path / "data"
    base.mkdir()
    (base / "u1").mkdir()
    # _validate_file_size calls path.stat() which raises built-in OSError
    # because the custom FileNotFoundError in data_service shadows the builtin
    with pytest.raises(OSError):
        preview_pickle_file(base, "u1", "missing.pkl")


def test_preview_deserialization_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(data_service, "_ALLOW_UNSAFE_DESERIALIZE", False)
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    (user / "x.pkl").write_bytes(b"data")
    with pytest.raises(DeserializationDisabledError):
        preview_pickle_file(base, "u1", "x.pkl")


# ── extract_series – more branches ────────────────────────────────────────


def test_extract_series_dataframe_with_explicit_x_column(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"ts": ["2020-01", "2020-02", "2020-03"], "val": [1, 2, 3]})
    (user / "df.pkl").write_bytes(pickle.dumps(df))
    res = extract_series(base, "u1", "df.pkl", x_column="ts", y_column="val")
    assert res["x"] == ["2020-01", "2020-02", "2020-03"]
    assert res["y"] == [1.0, 2.0, 3.0]


def test_extract_series_dataframe_auto_pick_y_column(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"label": ["a", "b"], "amount": [100.0, 200.0]})
    (user / "df.pkl").write_bytes(pickle.dumps(df))
    # y_column 'missing' is not in df, auto-picks numeric
    res = extract_series(base, "u1", "df.pkl", x_column=None, y_column="missing")
    assert "y" in res
    assert len(res["y"]) == 2


def test_extract_series_dataframe_date_column(tmp_path):
    """When no x_column and no datetime index, fall back to 'date' column."""
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"date": ["2020-01-01", "2020-01-02"], "val": [5, 6]})
    (user / "df.pkl").write_bytes(pickle.dumps(df))
    res = extract_series(base, "u1", "df.pkl", x_column=None, y_column="val")
    assert "x" in res


def test_extract_series_dataframe_no_numeric_column_raises(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"label": ["a", "b"], "name": ["x", "y"]})
    (user / "df.pkl").write_bytes(pickle.dumps(df))
    with pytest.raises(ValueError, match="No numeric column"):
        extract_series(base, "u1", "df.pkl", x_column=None, y_column="missing")


def test_extract_series_dataframe_missing_x_column_uses_index(tmp_path):
    """x_column specified but not found – fall back to datetime index."""
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    dates = pd.date_range("2021-01-01", periods=3, freq="D")
    df = pd.DataFrame({"val": [1, 2, 3]}, index=dates)
    (user / "df.pkl").write_bytes(pickle.dumps(df))
    res = extract_series(base, "u1", "df.pkl", x_column="nonexistent", y_column="val")
    assert len(res["x"]) == 3


def test_extract_series_dataframe_range_index_fallback(tmp_path):
    """x_column specified but not found, and index is not datetime -> use range."""
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"val": [1, 2, 3]})
    (user / "df.pkl").write_bytes(pickle.dumps(df))
    res = extract_series(base, "u1", "df.pkl", x_column="noexist", y_column="val")
    assert res["x"] == ["0", "1", "2"]


def test_extract_series_pandas_series(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    s = pd.Series([10.0, 20.0, 30.0], name="price")
    (user / "s.pkl").write_bytes(pickle.dumps(s))
    res = extract_series(base, "u1", "s.pkl", x_column=None, y_column="price")
    assert res["meta"]["series_name"] == "price"
    assert len(res["y"]) == 3


def test_extract_series_dict(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    d = {"prices": [1.0, 2.0, 3.0]}
    (user / "d.pkl").write_bytes(pickle.dumps(d))
    res = extract_series(base, "u1", "d.pkl", x_column=None, y_column="prices")
    assert "y" in res
    assert res["meta"]["key_used"] == "prices"


def test_extract_series_dict_no_numeric_raises(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    d = {"labels": ["a", "b", "c"]}
    (user / "d.pkl").write_bytes(pickle.dumps(d))
    with pytest.raises(ValueError, match="Could not extract numeric series"):
        extract_series(base, "u1", "d.pkl", x_column=None, y_column="unused")


def test_extract_series_list(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    lst = [1.0, 2.0, 3.0, 4.0]
    (user / "lst.pkl").write_bytes(pickle.dumps(lst))
    res = extract_series(base, "u1", "lst.pkl", x_column=None, y_column="unused")
    assert len(res["y"]) == 4
    assert res["meta"]["kind"] == "list"


def test_extract_series_unsupported_type_raises(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    (user / "obj.pkl").write_bytes(pickle.dumps(object()))
    with pytest.raises(ValueError, match="Unsupported pickle object"):
        extract_series(base, "u1", "obj.pkl", x_column=None, y_column="x")


def test_extract_series_max_points_trim(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"val": range(100)})
    (user / "df.pkl").write_bytes(pickle.dumps(df))
    res = extract_series(
        base, "u1", "df.pkl", x_column=None, y_column="val", max_points=10
    )
    assert len(res["y"]) == 10


def test_list_pickles_sorts_by_name(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    for name in ["c.pkl", "a.pkl", "b.pkl"]:
        df = pd.DataFrame({"x": [1]})
        df.to_pickle(user / name)
    result = data_service.list_pickles_for_user(base, "u1")
    names = [f["filename"] for f in result]
    assert names == sorted(names)


def test_list_pickles_includes_pickle_extension(tmp_path):
    base = tmp_path / "data"
    user = base / "u1"
    user.mkdir(parents=True)
    df = pd.DataFrame({"x": [1]})
    df.to_pickle(user / "data.pickle")
    result = data_service.list_pickles_for_user(base, "u1")
    assert any(f["filename"] == "data.pickle" for f in result)
