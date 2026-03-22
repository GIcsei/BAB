from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class FileItem(BaseModel):
    filename: str
    size_bytes: int
    modified_ms: int


class FileListResponse(BaseModel):
    files: List[FileItem]
    total_count: int


class ColumnInfo(BaseModel):
    name: str
    dtype: str


class SeriesMeta(BaseModel):
    n_points: int
    y_column: Optional[str] = None
    series_name: Optional[str] = None
    key_used: Optional[str] = None
    shape: Optional[Any] = None
    kind: Optional[str] = None


class SeriesResponse(BaseModel):
    x: List[Any]
    y: List[float]
    meta: SeriesMeta


class PreviewResponse(BaseModel):
    preview: Dict[str, Any]
