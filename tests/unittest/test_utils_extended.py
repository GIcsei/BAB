"""Extended tests for app.core.firestore_handler.Utils – raise_detailed_error and more."""

from unittest.mock import MagicMock

import pytest
from app.core.firestore_handler.Utils import (
    DocumentKeyGenerator,
    KeepAuthSession,
    raise_detailed_error,
)
from requests.exceptions import HTTPError

# ── raise_detailed_error ───────────────────────────────────────────────────


def test_raise_detailed_error_ok():
    """No error is raised when the response status is ok."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()  # does not raise
    raise_detailed_error(resp)  # should not raise


def test_raise_detailed_error_raises_http_error():
    """HTTPError is re-raised with response text appended."""
    resp = MagicMock()
    resp.text = "Permission denied"
    resp.raise_for_status.side_effect = HTTPError("403 Client Error")

    with pytest.raises(HTTPError):
        raise_detailed_error(resp)


# ── KeepAuthSession ────────────────────────────────────────────────────────


def test_keep_auth_session_rebuild_auth_strips_cross_domain_auth():
    """Authorization header is dropped when redirected to another domain."""
    session = KeepAuthSession()
    prepared_request = MagicMock()
    prepared_request.headers = {"Authorization": "Bearer token"}
    prepared_request.url = "https://other.example/resource"

    response = MagicMock()
    response.request.url = "https://api.example/resource"

    session.rebuild_auth(prepared_request, response)

    assert "Authorization" not in prepared_request.headers


def test_keep_auth_session_rebuild_auth_keeps_same_domain_auth():
    """Authorization header remains when redirect stays on same domain."""
    session = KeepAuthSession()
    prepared_request = MagicMock()
    prepared_request.headers = {"Authorization": "Bearer token"}
    prepared_request.url = "https://api.example/next"

    response = MagicMock()
    response.request.url = "https://api.example/start"

    session.rebuild_auth(prepared_request, response)

    assert prepared_request.headers["Authorization"] == "Bearer token"


def test_keep_auth_session_is_requests_session():
    from requests import Session

    session = KeepAuthSession()
    assert isinstance(session, Session)


# ── DocumentKeyGenerator unique keys ──────────────────────────────────────


def test_document_key_generator_sequential_keys_are_valid():
    gen = DocumentKeyGenerator()
    keys = [gen.generate_key() for _ in range(20)]
    valid_chars = set(
        "-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz"
    )
    for key in keys:
        assert len(key) == 20
        assert all(c in valid_chars for c in key)
