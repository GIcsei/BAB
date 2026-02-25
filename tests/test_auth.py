"""Tests for app.core.auth – get_current_user_id."""

import os

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

from unittest.mock import MagicMock

import pytest
from app.core.auth import get_current_user_id
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials


def _make_creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


# ── get_current_user_id ───────────────────────────────────────────────────


def test_get_current_user_id_via_verify_id_token():
    """If verify_id_token returns a dict with user_id, return it."""
    mock_fb = MagicMock()
    mock_fb.verify_id_token.return_value = {"user_id": "firebase_uid"}
    mock_fb.get_user_id_by_token.return_value = None

    user_id = get_current_user_id(creds=_make_creds("valid_token"), firebase=mock_fb)

    assert user_id == "firebase_uid"


def test_get_current_user_id_fallback_to_in_memory_token():
    """If verify_id_token returns None, fall back to in-memory registry."""
    mock_fb = MagicMock()
    mock_fb.verify_id_token.return_value = None
    mock_fb.get_user_id_by_token.return_value = "legacy_user"

    user_id = get_current_user_id(creds=_make_creds("legacy_token"), firebase=mock_fb)

    assert user_id == "legacy_user"


def test_get_current_user_id_no_user_id_in_verified_token():
    """If verify_id_token returns dict without user_id, use in-memory fallback."""
    mock_fb = MagicMock()
    mock_fb.verify_id_token.return_value = {"email": "user@example.com"}
    mock_fb.get_user_id_by_token.return_value = "mem_user"

    user_id = get_current_user_id(creds=_make_creds("some_token"), firebase=mock_fb)

    assert user_id == "mem_user"


def test_get_current_user_id_raises_when_no_user_found():
    """If both verify and in-memory fail, raise HTTPException 401."""
    mock_fb = MagicMock()
    mock_fb.verify_id_token.return_value = None
    mock_fb.get_user_id_by_token.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(creds=_make_creds("bad_token"), firebase=mock_fb)

    assert exc_info.value.status_code == 401


def test_get_current_user_id_verify_throws_raises_401():
    """If verify_id_token throws exception, raise HTTPException 401."""
    mock_fb = MagicMock()
    mock_fb.verify_id_token.side_effect = RuntimeError("network error")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(creds=_make_creds("token"), firebase=mock_fb)

    assert exc_info.value.status_code == 401
