import asyncio
import builtins
import logging
import pickle
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.core.exceptions import (
    DeserializationDisabledError,
    DeserializationError,
    FileNotFoundError,
    FileSizeExceededError,
)

logger = logging.getLogger(__name__)

_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="data_service")
    return _executor


def _allow_unsafe_deserialize() -> bool:
    return get_settings().allow_unsafe_deserialize


def _safe_basename(filename: str) -> str:
    return Path(filename).name


def _validate_file_size(path: Path, max_size_mb: int = 500) -> None:
    """Prevent loading extremely large files that could exhaust memory."""
    try:
        size_bytes = path.stat().st_size
        if size_bytes > max_size_mb * 1024 * 1024:
            size_mb = size_bytes // (1024 * 1024)
            raise FileSizeExceededError(size_mb, max_size_mb)
    except builtins.FileNotFoundError as exc:
        logger.debug("File not found during size validation: %s", path)
        raise FileNotFoundError(str(path)) from exc


def list_data_files_for_user(base_data_dir: Path, user_id: str) -> List[Dict[str, Any]]:
    user_dir = base_data_dir / user_id
    out: List[Dict[str, Any]] = []
    if not user_dir.exists() or not user_dir.is_dir():
        return out
    try:
        for p in sorted(user_dir.iterdir(), key=lambda x: x.name):
            if p.is_file() and p.suffix.lower() in {".pkl", ".pickle", ".csv", ".parquet"}:
                try:
                    out.append(
                        {
                            "filename": p.name,
                            "size_bytes": p.stat().st_size,
                            "modified_ms": int(p.stat().st_mtime * 1000),
                        }
                    )
                except Exception:
                    logger.exception("Error reading file metadata: %s", p)
    except Exception:
        logger.exception("Error listing data files in directory: %s", user_dir)
    return out


# Backward-compatible alias
list_pickles_for_user = list_data_files_for_user


def _try_load(path: Path) -> Any:
    if not _allow_unsafe_deserialize():
        raise DeserializationDisabledError(
            "Unsafe deserialization is disabled. Set APP_ALLOW_UNSAFE_DESERIALIZE=true "
            "to enable (not recommended)."
        )

    try:
        import joblib  # type: ignore
    except Exception:
        joblib = None

    last_exc = None
    if joblib is not None:
        try:
            return joblib.load(path)
        except Exception as exc:
            last_exc = exc
            logger.debug("joblib.load failed for %s: %s", path, exc)

    try:
        return pd.read_pickle(path)
    except Exception as exc:
        last_exc = exc
        logger.debug("pandas.read_pickle failed for %s: %s", path, exc)

    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as exc:
        logger.exception("All deserialization attempts failed for %s", path)
        raise DeserializationError(str(path), str(last_exc or exc))


def _load_file(path: Path) -> Any:
    """Load a data file based on its extension."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    elif suffix == ".parquet":
        return pd.read_parquet(path)
    else:
        return _try_load(path)


def _to_json_serializable(obj: Any, max_rows: int = 200) -> Dict[str, Any]:
    try:
        if isinstance(obj, pd.DataFrame):
            rows = obj.head(max_rows).to_dict(orient="records")
            columns = [{"name": c, "dtype": str(obj[c].dtype)} for c in obj.columns]
            return {
                "type": "dataframe",
                "columns": columns,
                "rows": rows,
                "n_rows": int(obj.shape[0]),
            }
        if isinstance(obj, pd.Series):
            values = obj.head(max_rows).tolist()
            index = obj.head(max_rows).index.tolist()
            return {
                "type": "series",
                "index": index,
                "values": values,
                "n_rows": int(obj.shape[0]),
            }
        if isinstance(obj, np.ndarray):
            flat = obj.ravel()
            lst = flat[:max_rows].tolist()
            return {
                "type": "ndarray",
                "shape": obj.shape,
                "values": lst,
                "n_items": int(flat.size),
            }
        if isinstance(obj, (list, tuple)):

            def conv_item(i: Any) -> Any:
                if isinstance(i, (str, int, float, bool, type(None))):
                    return i
                if isinstance(i, (dict, list)):
                    return i
                try:
                    return str(i)
                except Exception:
                    return None

            return {
                "type": "list",
                "sample": [conv_item(x) for x in list(obj)[:max_rows]],
                "length": len(obj),
            }
        if isinstance(obj, dict):
            sample: Dict[str, Any] = {}
            for k, v in list(obj.items())[:50]:
                if isinstance(v, (str, int, float, bool, type(None))):
                    sample[k] = v
                else:
                    sample[k] = str(type(v))
            return {
                "type": "dict",
                "sample_keys": list(sample.keys()),
                "sample": sample,
            }
        return {"type": "unknown", "repr": str(obj)}
    except Exception:
        logger.exception("Failed to convert object to JSON serializable")
        return {"type": "error", "repr": str(obj)}


def preview_pickle_file(
    base_data_dir: Path, user_id: str, filename: str, max_rows: int = 200
) -> Dict[str, Any]:
    safe_name = _safe_basename(filename)
    path = base_data_dir / user_id / safe_name
    _validate_file_size(path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))
    obj = _load_file(path)
    return _to_json_serializable(obj, max_rows=max_rows)


async def preview_pickle_file_async(
    base_data_dir: Path, user_id: str, filename: str, max_rows: int = 200
) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _get_executor(),
        preview_pickle_file,
        base_data_dir,
        user_id,
        filename,
        max_rows,
    )


def extract_series(
    base_data_dir: Path,
    user_id: str,
    filename: str,
    x_column: Optional[str],
    y_column: str,
    max_points: int = 10000,
) -> Dict[str, Any]:
    safe_name = _safe_basename(filename)
    path = base_data_dir / user_id / safe_name
    _validate_file_size(path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))

    obj = _load_file(path)

    if isinstance(obj, pd.DataFrame):
        df = obj
        if y_column not in df.columns:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if not numeric_cols:
                raise ValueError("No numeric column available for y")
            y_column = numeric_cols[0]
        y = df[y_column].dropna().astype(float)
        x: Any
        if x_column:
            if x_column in df.columns:
                x = df[x_column]
            else:
                if pd.api.types.is_datetime64_any_dtype(df.index):
                    x = df.index
                else:
                    x = list(range(len(y)))
        else:
            if pd.api.types.is_datetime64_any_dtype(df.index):
                x = df.index
            elif "date" in df.columns:
                x = df["date"]
            else:
                x = list(range(len(y)))
        length = min(len(y), max_points)
        x_vals = pd.Series(x).head(length).astype(str).tolist()
        y_vals = y.head(length).tolist()
        return {
            "x": x_vals,
            "y": y_vals,
            "meta": {"y_column": y_column, "n_points": length},
        }

    if isinstance(obj, pd.Series):
        s = obj.dropna().astype(float)
        x_vals = s.head(max_points).index.astype(str).tolist()
        y_vals = s.head(max_points).tolist()
        return {
            "x": x_vals,
            "y": y_vals,
            "meta": {"series_name": getattr(s, "name", None), "n_points": len(y_vals)},
        }

    if isinstance(obj, np.ndarray):
        arr = obj.flatten()
        length = min(arr.size, max_points)
        return {
            "x": list(range(length)),
            "y": arr[:length].astype(float).tolist(),
            "meta": {"shape": obj.shape},
        }

    if isinstance(obj, (list, tuple)):
        arr = np.array(obj, dtype=float)
        length = min(arr.size, max_points)
        return {
            "x": list(range(length)),
            "y": arr[:length].tolist(),
            "meta": {"kind": "list"},
        }

    if isinstance(obj, dict):
        for k, v in obj.items():
            try:
                arr = np.array(v, dtype=float)
                length = min(arr.size, max_points)
                return {
                    "x": list(range(length)),
                    "y": arr[:length].tolist(),
                    "meta": {"key_used": k},
                }
            except Exception:
                continue
        raise ValueError("Could not extract numeric series from dict")

    raise ValueError("Unsupported pickle object for series extraction")


async def extract_series_async(
    base_data_dir: Path,
    user_id: str,
    filename: str,
    x_column: Optional[str],
    y_column: str,
    max_points: int = 10000,
) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _get_executor(),
        extract_series,
        base_data_dir,
        user_id,
        filename,
        x_column,
        y_column,
        max_points,
    )
