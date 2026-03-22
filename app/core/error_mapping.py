"""
Map typed exceptions to HTTP responses.
Centralizes error-to-response logic for consistent API behavior.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import HTTPException

from app.core.exceptions import (
    AppException,
)


def exception_to_http(exc: Exception) -> HTTPException:
    """
    Convert an AppException (or generic Exception) to FastAPI HTTPException.
    Provides consistent error response format.
    """
    if isinstance(exc, AppException):
        return HTTPException(
            status_code=exc.status_code,
            detail={
                "error": exc.code,
                "message": exc.message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    # Fallback for non-App exceptions (e.g., validation errors)
    return HTTPException(
        status_code=500,
        detail={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


def get_error_response(exc: Exception) -> Dict[str, Any]:
    """
    Return error response dict (for non-HTTPException contexts, e.g., middleware).
    """
    if isinstance(exc, AppException):
        return {
            "error": exc.code,
            "message": exc.message,
            "status": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    return {
        "error": "INTERNAL_ERROR",
        "message": "An unexpected error occurred",
        "status": 500,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
