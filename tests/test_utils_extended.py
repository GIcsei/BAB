"""Extended tests for app.core.firestore_handler.Utils – raise_detailed_error and more."""
import pytest
from unittest.mock import MagicMock
from requests.exceptions import HTTPError

from app.core.firestore_handler.Utils import (
    KeepAuthSession,
    raise_detailed_error,
    DocumentKeyGenerator,
)


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


def test_keep_auth_session_rebuild_auth_is_noop():
    """rebuild_auth should not do anything (passes)."""
    session = KeepAuthSession()
    # Should not raise or do anything
    session.rebuild_auth(MagicMock(), MagicMock())


def test_keep_auth_session_is_requests_session():
    from requests import Session

    session = KeepAuthSession()
    assert isinstance(session, Session)


# ── DocumentKeyGenerator unique keys ──────────────────────────────────────


def test_document_key_generator_sequential_keys_are_valid():
    gen = DocumentKeyGenerator()
    keys = [gen.generate_key() for _ in range(20)]
    valid_chars = set("-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz")
    for key in keys:
        assert len(key) == 20
        assert all(c in valid_chars for c in key)
