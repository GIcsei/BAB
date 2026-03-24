import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_current_user_id
from app.core.config import get_settings
from app.core.error_mapping import exception_to_http
from app.core.exceptions import (
    DeserializationError,
    FileNotFoundError,
    FileSizeExceededError,
)
from app.schemas.data import FileItem, FileListResponse, PreviewResponse, SeriesResponse
from app.services import data_service

router = APIRouter(prefix="/data", tags=["Data"])
logger = logging.getLogger(__name__)


def _base_dir() -> Path:
    return get_settings().app_user_data_dir


def _validate_user_id(user_id: str) -> str:
    """Validate user_id format to prevent path traversal."""
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", user_id):
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Invalid user_id format")
    return user_id


def _validate_filename(filename: str) -> str:
    """Validate filename to ensure only supported data files are accessed."""
    if not re.match(
        r"^[a-zA-Z0-9_\-\.]+\.(csv|parquet|json)$", filename, re.IGNORECASE
    ):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail="Invalid filename format; only .csv, .parquet, and .json files are allowed",
        )
    return filename


@router.get(
    "/list",
    response_model=FileListResponse,
    summary="List available data files (CSV, Parquet, JSON) for authenticated user",
)
async def list_files(
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=500, description="Maximum files per page"),
    current_user_id: str = Depends(get_current_user_id),
) -> FileListResponse:
    user_id = _validate_user_id(current_user_id)
    try:
        all_files = data_service.list_data_files_for_user(_base_dir(), user_id)
        total_count = len(all_files)
        paginated = all_files[offset : offset + limit]
        return FileListResponse(
            files=[FileItem(**f) for f in paginated], total_count=total_count
        )
    except Exception as exc:
        logger.exception("Error listing data files for user %s", user_id)
        raise exception_to_http(exc)


@router.get(
    "/files/{filename}/preview",
    response_model=PreviewResponse,
    summary="Preview contents of a data file",
)
async def preview_file(
    filename: str,
    rows: int = Query(200, ge=1, le=5000),
    current_user_id: str = Depends(get_current_user_id),
) -> PreviewResponse:
    user_id = _validate_user_id(current_user_id)
    filename = _validate_filename(filename)
    try:
        preview = await data_service.preview_pickle_file_async(
            _base_dir(), user_id, filename, max_rows=rows
        )
        return PreviewResponse(preview=preview)
    except FileNotFoundError as exc:
        logger.warning("File not found: %s/%s", user_id, filename)
        raise exception_to_http(exc)
    except FileSizeExceededError as exc:
        logger.warning("File size exceeded for %s/%s", user_id, filename)
        raise exception_to_http(exc)
    except DeserializationError as exc:
        logger.warning(
            "Deserialization error for %s/%s: %s", user_id, filename, exc.message
        )
        raise exception_to_http(exc)
    except Exception as exc:
        logger.exception("Unexpected error previewing file %s/%s", user_id, filename)
        raise exception_to_http(exc)


@router.get(
    "/files/{filename}/series",
    response_model=SeriesResponse,
    summary="Extract x/y series for plotting",
)
async def get_series(
    filename: str,
    y: str = Query(..., description="Column or series name to use as Y"),
    x: Optional[str] = Query(
        None, description="Optional X column (or leave empty to use index/datetime)"
    ),
    max_points: int = Query(10000, ge=10, le=100000),
    current_user_id: str = Depends(get_current_user_id),
) -> Dict[str, Any]:
    user_id = _validate_user_id(current_user_id)
    filename = _validate_filename(filename)
    try:
        series = await data_service.extract_series_async(
            _base_dir(),
            user_id,
            filename,
            x_column=x,
            y_column=y,
            max_points=max_points,
        )
        return series
    except FileNotFoundError as exc:
        logger.warning("File not found: %s/%s", user_id, filename)
        raise exception_to_http(exc)
    except FileSizeExceededError as exc:
        logger.warning("File size exceeded for %s/%s", user_id, filename)
        raise exception_to_http(exc)
    except DeserializationError as exc:
        logger.warning(
            "Deserialization error for %s/%s: %s", user_id, filename, exc.message
        )
        raise exception_to_http(exc)
    except ValueError as exc:
        logger.warning("Invalid parameters for series extraction: %s", exc)
        raise exception_to_http(DeserializationError(filename, str(exc)))
    except Exception as exc:
        logger.exception(
            "Unexpected error extracting series from %s/%s", user_id, filename
        )
        raise exception_to_http(exc)
