"""Tests for remaining QueryHandler / TokenService / TokenPersistence coverage."""

import asyncio
import json
from unittest.mock import MagicMock, patch

import app.core.firestore_handler.QueryHandler as qh_mod
import pytest
from app.application.services.token_service import TokenPersistence
from app.core.firestore_handler.QueryHandler import initialize_app


@pytest.fixture(autouse=True)
def restore_singleton():
    original = qh_mod._DEFAULT_FIREBASE
    yield
    qh_mod._DEFAULT_FIREBASE = original


def _make_fb_with_api_key():
    fb = initialize_app({"projectId": "p"})
    fb.api_key = "test-key"
    return fb


# ── TokenPersistence._write_json failure ──────────────────────────────────


def test_write_json_failure_returns_false(tmp_path):
    """_write_json returns False when writing fails."""
    path = tmp_path / "tok.json"
    with patch("builtins.open", side_effect=PermissionError("denied")):
        result = TokenPersistence._write_json(path, {"key": "val"})
    assert result is False


# ── TokenPersistence async methods ────────────────────────────────────────


def test_read_json_async(tmp_path):
    """read_json_async should work in an async context."""
    path = tmp_path / "tok.json"
    path.write_text('{"foo": "bar"}')
    p = TokenPersistence()

    result = asyncio.get_event_loop().run_until_complete(p.read_json_async(path))
    assert result == {"foo": "bar"}


def test_write_json_async(tmp_path):
    """write_json_async should persist data asynchronously."""
    path = tmp_path / "out.json"
    p = TokenPersistence()

    result = asyncio.get_event_loop().run_until_complete(
        p.write_json_async(path, {"async": True})
    )
    assert result is True
    assert json.loads(path.read_text()) == {"async": True}


# ── TokenService._ensure_auth_client creates new client ──────────────────


def test_ensure_auth_client_creates_new(tmp_path):
    """_ensure_auth_client creates an Auth instance when _auth_client is None."""
    fb = _make_fb_with_api_key()
    fb.token_service._auth_client = None  # force None

    auth_client = fb.token_service._ensure_auth_client()
    assert auth_client is not None
    from app.core.firestore_handler.User import Auth

    assert isinstance(auth_client, Auth)


# ── load_tokens_from_dir – file (not dir) skip ────────────────────────────


def test_load_tokens_skips_non_dirs(tmp_path):
    """load_tokens_from_dir skips regular files in the base_dir."""
    fb = _make_fb_with_api_key()
    fb.token_service._auth_client = MagicMock()

    # Create a file (not a dir) in tmp_path
    (tmp_path / "somefile.txt").write_text("data")
    # Create a dir but no credentials.json
    (tmp_path / "user_dir").mkdir()

    fb.load_tokens_from_dir(tmp_path, refresh=False)
    # Just check no exception was raised
    assert fb.get_user_token("somefile.txt") is None


# ── register_user_tokens – write exception ────────────────────────────────


def test_register_user_tokens_write_exception(tmp_path):
    """register_user_tokens handles exception when persisting credentials."""
    fb = _make_fb_with_api_key()
    cred_path = tmp_path / "u1" / "credentials.json"
    cred_path.parent.mkdir()

    with patch.object(
        fb.token_service._persistence, "write_json", side_effect=OSError("no space")
    ):
        # Should not raise
        fb.register_user_tokens("u1", {"idToken": "tok"}, credentials_path=cred_path)

    # token should still be registered in memory
    assert fb.get_user_token("u1") is not None


# ── refresh_token – persistence failure ──────────────────────────────────


def test_refresh_token_persistence_failure(tmp_path, monkeypatch):
    """refresh_token continues if persistence write fails."""
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))
    fb = _make_fb_with_api_key()
    fb.token_service._registry.register("u1", {"idToken": "old", "refreshToken": "ref"})

    mock_auth = MagicMock()
    mock_auth.refresh.return_value = {"idToken": "new", "refreshToken": "new_ref"}
    fb.token_service._auth_client = mock_auth

    with patch.object(
        fb.token_service._persistence, "write_json", side_effect=OSError("disk full")
    ):
        result = fb.refresh_token("u1")

    # Token was still refreshed in memory
    assert result["idToken"] == "new"


# ── clear_user – active user token reset ─────────────────────────────────


def test_clear_user_removes_token():
    """clear_user removes a user's token from the registry."""
    fb = _make_fb_with_api_key()
    fb.token_service._registry.register("u1", {"idToken": "tok", "userId": "u1"})

    fb.clear_user("u1")

    assert fb.get_user_token("u1") is None


def test_clear_user_does_not_affect_other_users():
    """clear_user does NOT remove other users' tokens."""
    fb = _make_fb_with_api_key()
    fb.token_service._registry.register("u1", {"idToken": "tok1"})
    fb.token_service._registry.register("u2", {"idToken": "tok2"})

    fb.clear_user("u1")

    # u2's token should remain
    assert fb.get_user_token("u2") is not None
    assert fb.get_user_token("u2")["idToken"] == "tok2"


# ── verify_id_token in non-test mode ─────────────────────────────────────


def test_verify_id_token_returns_none_in_test_mode():
    """In test mode, verify_id_token returns None without calling firebase-admin."""
    fb = _make_fb_with_api_key()
    result = fb.verify_id_token("some_token")
    # In test mode (PYTEST_RUNNING=1), returns None
    assert result is None


def test_verify_id_token_empty_token_returns_none():
    """verify_id_token returns None for empty token."""
    fb = _make_fb_with_api_key()
    result = fb.verify_id_token("")
    assert result is None


def test_verify_id_token_uses_firebase_admin_in_non_test_mode():
    """In non-test mode, verify_id_token delegates to firebase-admin."""
    fb = _make_fb_with_api_key()

    mock_decoded = {"uid": "real_uid", "email": "user@example.com"}

    with (
        patch(
            "app.infrastructure.firebase.auth.is_testing_env",
            return_value=False,
        ),
        patch(
            "app.infrastructure.firebase.auth.initialize_firebase_admin",
            return_value=MagicMock(),
        ),
        patch(
            "app.infrastructure.firebase.auth.fauth.verify_id_token",
            return_value=mock_decoded,
        ),
    ):
        result = fb.verify_id_token("real_token")

    assert result["user_id"] == "real_uid"
    assert result["email"] == "user@example.com"


def test_verify_id_token_firebase_admin_exception():
    """verify_id_token returns None if firebase-admin raises an exception."""
    fb = _make_fb_with_api_key()

    with (
        patch(
            "app.infrastructure.firebase.auth.is_testing_env",
            return_value=False,
        ),
        patch(
            "app.infrastructure.firebase.auth.initialize_firebase_admin",
            return_value=MagicMock(),
        ),
        patch(
            "app.infrastructure.firebase.auth.fauth.verify_id_token",
            side_effect=Exception("auth error"),
        ),
    ):
        result = fb.verify_id_token("bad_token")

    assert result is None
