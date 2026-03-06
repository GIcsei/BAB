"""Tests for app.core.error_mapping."""

from app.core.error_mapping import exception_to_http, get_error_response
from app.core.exceptions import (
    AppException,
    FirebaseError,
    InvalidTokenError,
    LoginFailedError,
)
from app.core.exceptions import FileNotFoundError as AppFileNotFoundError
from fastapi import HTTPException

# ── exception_to_http ──────────────────────────────────────────────────────


def test_exception_to_http_with_app_exception():
    exc = InvalidTokenError()
    http_exc = exception_to_http(exc)
    assert isinstance(http_exc, HTTPException)
    assert http_exc.status_code == 401
    assert http_exc.detail["error"] == "INVALID_TOKEN"
    assert "Invalid" in http_exc.detail["message"]


def test_exception_to_http_with_file_not_found():
    exc = AppFileNotFoundError("data.pkl")
    http_exc = exception_to_http(exc)
    assert http_exc.status_code == 404
    assert http_exc.detail["error"] == "FILE_NOT_FOUND"
    assert "data.pkl" in http_exc.detail["message"]


def test_exception_to_http_with_firebase_error():
    exc = FirebaseError("db unavailable")
    http_exc = exception_to_http(exc)
    assert http_exc.status_code == 502
    assert http_exc.detail["error"] == "FIREBASE_ERROR"


def test_exception_to_http_with_generic_exception():
    exc = RuntimeError("something broke")
    http_exc = exception_to_http(exc)
    assert isinstance(http_exc, HTTPException)
    assert http_exc.status_code == 500
    assert http_exc.detail["error"] == "INTERNAL_ERROR"
    assert "unexpected" in http_exc.detail["message"].lower()


def test_exception_to_http_with_value_error():
    exc = ValueError("bad value")
    http_exc = exception_to_http(exc)
    assert http_exc.status_code == 500


# ── get_error_response ─────────────────────────────────────────────────────


def test_get_error_response_with_app_exception():
    exc = LoginFailedError("wrong password")
    resp = get_error_response(exc)
    assert resp["error"] == "LOGIN_FAILED"
    assert resp["message"] == "wrong password"
    assert resp["status"] == 401


def test_get_error_response_with_custom_app_exception():
    exc = AppException("custom", code="MY_CODE", status_code=422)
    resp = get_error_response(exc)
    assert resp["error"] == "MY_CODE"
    assert resp["status"] == 422


def test_get_error_response_with_generic_exception():
    exc = RuntimeError("unexpected failure")
    resp = get_error_response(exc)
    assert resp["error"] == "INTERNAL_ERROR"
    assert resp["status"] == 500
    # Internal error details must not be exposed to clients
    assert resp["message"] == "An unexpected error occurred"


def test_get_error_response_with_empty_message():
    exc = RuntimeError("")
    resp = get_error_response(exc)
    assert resp["error"] == "INTERNAL_ERROR"
    assert resp["message"] == "An unexpected error occurred"
