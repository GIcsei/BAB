from fastapi import APIRouter, HTTPException, Query, Depends
from pathlib import Path
import logging
import os

from app.core.auth import get_current_user_id
from app.services import data_service

router = APIRouter(prefix="/data", tags=["Data"])
logger = logging.getLogger(__name__)


def _base_dir() -> Path:
    return Path(os.getenv("APP_USER_DATA_DIR", "/var/app/user_data"))


@router.get("/list", summary="List available pickle files for authenticated user")
def list_files(current_user_id: str = Depends(get_current_user_id)):
    try:
        files = data_service.list_pickles_for_user(_base_dir(), current_user_id)
        return {"files": files}
    except Exception as e:
        logger.exception("Error listing pickles for user %s", current_user_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{filename}/preview", summary="Preview contents of a pickle file")
def preview_file(filename: str, rows: int = Query(200, ge=1, le=5000), current_user_id: str = Depends(get_current_user_id)):
    try:
        preview = data_service.preview_pickle_file(_base_dir(), current_user_id, filename, max_rows=rows)
        return {"preview": preview}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        logger.exception("Error previewing file %s/%s: %s", current_user_id, filename, e)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/files/{filename}/series", summary="Extract x/y series for plotting")
def get_series(
    filename: str,
    y: str = Query(..., description="Column or series name to use as Y"),
    x: str = Query(None, description="Optional X column (or leave empty to use index/datetime)"),
    max_points: int = Query(10000, ge=10, le=100000),
    current_user_id: str = Depends(get_current_user_id),
):
    try:
        series = data_service.extract_series(_base_dir(), current_user_id, filename, x_column=x, y_column=y, max_points=max_points)
        return series
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception("Error extracting series from %s/%s: %s", current_user_id, filename, e)
        raise HTTPException(status_code=500, detail="Internal server error")
