"""Additional QueryHandler tests – refresh_token, auth, and more Firebase methods."""
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import app.core.firestore_handler.QueryHandler as qh_mod
from app.core.firestore_handler.QueryHandler import Firebase, initialize_app


@pytest.fixture(autouse=True)
def setup_and_teardown():
    original = qh_mod._DEFAULT_FIREBASE
    yield
    qh_mod._DEFAULT_FIREBASE = original


def _make_fb_with_api_key():
    fb = initialize_app({"projectId": "p"})
    fb.api_key = "test-key"
    return fb


# ── Firebase.auth ──────────────────────────────────────────────────────────


def test_auth_with_no_existing_token(tmp_path):
    """Firebase.auth should return auth_client and None when no token file exists."""
    fb = _make_fb_with_api_key()
    token_path = tmp_path / "tok.json"

    mock_auth_client = MagicMock()
    fb._auth_client = mock_auth_client
    mock_auth_client.refresh.side_effect = Exception("no token")

    auth_client, token = fb.auth(token_path)
    assert auth_client is mock_auth_client
    assert token is None


def test_auth_with_existing_token_refreshes(tmp_path):
    """Firebase.auth should refresh existing token when available."""
    fb = _make_fb_with_api_key()
    token_path = tmp_path / "tok.json"
    token_path.write_text('{"idToken": "old", "refreshToken": "ref"}')

    mock_auth_client = MagicMock()
    mock_auth_client.refresh.return_value = {"idToken": "new", "refreshToken": "new_ref"}
    fb._auth_client = mock_auth_client

    auth_client, token = fb.auth(token_path)
    assert token["idToken"] == "new"


def test_auth_refresh_failure_returns_old_token(tmp_path):
    """If refresh fails, return the stored (old) token instead."""
    fb = _make_fb_with_api_key()
    token_path = tmp_path / "tok.json"
    stored = {"idToken": "old_tok", "refreshToken": "old_ref"}
    token_path.write_text(json.dumps(stored))

    mock_auth_client = MagicMock()
    mock_auth_client.refresh.side_effect = Exception("refresh failed")
    fb._auth_client = mock_auth_client

    _, token = fb.auth(token_path)
    assert token["idToken"] == "old_tok"


# ── Firebase.refresh_token ────────────────────────────────────────────────


def test_refresh_token_no_user_raises():
    fb = _make_fb_with_api_key()
    with pytest.raises(ValueError, match="No token found"):
        fb.refresh_token("nonexistent_user")


def test_refresh_token_success(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))
    fb = _make_fb_with_api_key()
    fb._registry.register("u1", {"idToken": "old", "refreshToken": "ref", "email": "u@e.com"})

    mock_auth_client = MagicMock()
    mock_auth_client.refresh.return_value = {
        "idToken": "new_tok",
        "refreshToken": "new_ref",
        "userId": "u1",
    }
    fb._auth_client = mock_auth_client

    result = fb.refresh_token("u1")
    assert result["idToken"] == "new_tok"
    assert result["email"] == "u@e.com"
    assert fb._registry.get("u1")["idToken"] == "new_tok"


def test_refresh_token_persists_to_dir(tmp_path, monkeypatch):
    """refresh_token should persist new token to credentials.json if dir exists."""
    monkeypatch.setenv("APP_USER_DATA_DIR", str(tmp_path))

    user_dir = tmp_path / "u2"
    user_dir.mkdir()

    fb = _make_fb_with_api_key()
    fb._registry.register("u2", {"idToken": "old", "refreshToken": "ref"})

    mock_auth_client = MagicMock()
    mock_auth_client.refresh.return_value = {
        "idToken": "persisted_tok",
        "refreshToken": "p_ref",
        "userId": "u2",
    }
    fb._auth_client = mock_auth_client

    fb.refresh_token("u2")
    cred_path = user_dir / "credentials.json"
    assert cred_path.exists()
    data = json.loads(cred_path.read_text())
    assert data["idToken"] == "persisted_tok"


# ── Firebase.load_tokens_from_dir with refresh ────────────────────────────


def test_load_tokens_refresh_success(tmp_path):
    fb = _make_fb_with_api_key()
    user_dir = tmp_path / "u3"
    user_dir.mkdir()
    stored = {
        "idToken": "old_tok",
        "refreshToken": "old_ref",
        "userId": "u3",
        "email": "u3@e.com",
    }
    (user_dir / "credentials.json").write_text(json.dumps(stored))

    mock_auth_client = MagicMock()
    mock_auth_client.refresh.return_value = {
        "userId": "u3",
        "idToken": "new_tok",
        "refreshToken": "new_ref",
    }
    fb._auth_client = mock_auth_client

    fb.load_tokens_from_dir(tmp_path, refresh=True)
    token = fb.get_user_token("u3")
    assert token["idToken"] == "new_tok"


def test_load_tokens_refresh_failure_uses_stored(tmp_path):
    """If refresh fails, fall back to stored token."""
    fb = _make_fb_with_api_key()
    user_dir = tmp_path / "u4"
    user_dir.mkdir()
    stored = {"idToken": "fallback_tok", "refreshToken": "ref", "userId": "u4"}
    (user_dir / "credentials.json").write_text(json.dumps(stored))

    mock_auth_client = MagicMock()
    mock_auth_client.refresh.side_effect = Exception("token expired")
    fb._auth_client = mock_auth_client

    fb.load_tokens_from_dir(tmp_path, refresh=True)
    token = fb.get_user_token("u4")
    # Falls back to stored token
    assert token is not None
