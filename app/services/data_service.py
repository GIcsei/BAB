import asyncio
import logging
import pickle
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Thread pool for blocking I/O operations
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="data_service")


def _safe_basename(filename: str) -> str:
    # prevent path traversal - only allow simple filenames
    return Path(filename).name


def _validate_file_size(path: Path, max_size_mb: int = 500) -> None:
    """Prevent loading extremely large files that could exhaust memory."""
    try:
        size_bytes = path.stat().st_size
        if size_bytes > max_size_mb * 1024 * 1024:
            raise ValueError(f"File exceeds maximum allowed size of {max_size_mb}MB")
    except FileNotFoundError:
        raise FileNotFoundError(str(path))


def list_pickles_for_user(base_data_dir: Path, user_id: str) -> List[Dict[str, Any]]:
    user_dir = base_data_dir / user_id
    out: List[Dict[str, Any]] = []
    if not user_dir.exists() or not user_dir.is_dir():
        return out
    for p in sorted(user_dir.iterdir(), key=lambda x: x.name):
        if p.is_file() and p.suffix.lower() in {".pkl", ".pickle"}:
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
    return out


def _try_load(path: Path) -> Any:
    """
    Try to load common serialized formats in a safe fallback order:
    - joblib.load (if joblib available)
    - pandas.read_pickle
    - pickle.load (fallback)
    May raise exception on corrupt/untrusted data. Callers should catch and log.
    """
    # Try joblib if installed (useful for sklearn objects / numpy-heavy dumps)
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

    # final fallback to built-in pickle
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as exc:
        logger.exception("All deserialization attempts failed for %s", path)
        # re-raise the last caught exception to preserve context
        raise last_exc or exc


def _to_json_serializable(obj: Any, max_rows: int = 200) -> Any:
    """
    Convert common scientific/data objects to JSON serializable structures:
    - pandas.DataFrame -> dict with columns + records (truncated)
    - pandas.Series -> dict {index: [...], values: [...]}
    - numpy arrays -> list (converted, truncated)
    - list/dict of simple types -> returned as-is (recursion limited)
    - otherwise -> str(obj)
    """
    try:
        if isinstance(obj, pd.DataFrame):
            # provide schema + sample rows
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
            # attempt to convert elements
            def conv_item(i):
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
            # shallow convert
            sample = {}
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
        # fallback
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
    obj = _try_load(path)
    return _to_json_serializable(obj, max_rows=max_rows)


async def preview_pickle_file_async(
    base_data_dir: Path, user_id: str, filename: str, max_rows: int = 200
) -> Dict[str, Any]:
    """Async wrapper to prevent blocking the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _executor,
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
    """
    Return {x: [...], y: [...], meta: {...}} suitable for plotting.
    If x_column is None and input is Series or DataFrame with datetime index, index -> x is used.
    If y_column is missing, attempt to pick a numeric column.
    """
    safe_name = _safe_basename(filename)
    path = base_data_dir / user_id / safe_name
    _validate_file_size(path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(str(path))

    obj = _try_load(path)

    # Convert DataFrame/Series/ndarray/list/dict to x/y arrays
    if isinstance(obj, pd.DataFrame):
        df = obj
        if y_column not in df.columns:
            # try to auto-pick numeric column
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            if not numeric_cols:
                raise ValueError("No numeric column available for y")
            y_column = numeric_cols[0]
        y = df[y_column].dropna().astype(float)
        if x_column:
            if x_column in df.columns:
                x = df[x_column]
            else:
                # if not found, but index is datetime-like use index
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
        # trim to max_points
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
        # try numeric list
        arr = np.array(obj, dtype=float)
        length = min(arr.size, max_points)
        return {
            "x": list(range(length)),
            "y": arr[:length].tolist(),
            "meta": {"kind": "list"},
        }

    if isinstance(obj, dict):
        # try to find a single numeric array inside
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

    # fallback: try to stringify and fail
    raise ValueError("Unsupported pickle object for series extraction")


async def extract_series_async(
    base_data_dir: Path,
    user_id: str,
    filename: str,
    x_column: Optional[str],
    y_column: str,
    max_points: int = 10000,
) -> Dict[str, Any]:
    """Async wrapper to prevent blocking the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _executor,
        extract_series,
        base_data_dir,
        user_id,
        filename,
        x_column,
        y_column,
        max_points,
    )
