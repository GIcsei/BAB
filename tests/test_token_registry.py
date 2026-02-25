"""Tests for TokenRegistry and TokenPersistence in QueryHandler."""
import json
from pathlib import Path

import pytest

from app.core.firestore_handler.QueryHandler import TokenPersistence, TokenRegistry


# ── TokenRegistry ──────────────────────────────────────────────────────────


def test_register_and_get():
    registry = TokenRegistry()
    registry.register("u1", {"idToken": "abc", "refreshToken": "def"})
    result = registry.get("u1")
    assert result is not None
    assert result["idToken"] == "abc"


def test_get_unknown_user_returns_none():
    registry = TokenRegistry()
    assert registry.get("nobody") is None


def test_get_returns_copy():
    registry = TokenRegistry()
    registry.register("u1", {"idToken": "abc"})
    r1 = registry.get("u1")
    r1["idToken"] = "modified"
    r2 = registry.get("u1")
    assert r2["idToken"] == "abc"


def test_remove_user():
    registry = TokenRegistry()
    registry.register("u1", {"idToken": "abc"})
    registry.remove("u1")
    assert registry.get("u1") is None


def test_remove_nonexistent_is_noop():
    registry = TokenRegistry()
    registry.remove("nobody")  # should not raise


def test_remove_clears_active_user():
    registry = TokenRegistry()
    registry.register("u1", {"idToken": "abc"})
    registry.set_active("u1")
    registry.remove("u1")
    assert registry.get_active_token() is None


def test_set_active_and_get_active_token():
    registry = TokenRegistry()
    registry.register("u1", {"idToken": "tok1"})
    registry.set_active("u1")
    token = registry.get_active_token()
    assert token is not None
    assert token["idToken"] == "tok1"


def test_set_active_unknown_user_raises():
    registry = TokenRegistry()
    with pytest.raises(ValueError, match="No token registered"):
        registry.set_active("nobody")


def test_get_active_token_no_active_user():
    registry = TokenRegistry()
    assert registry.get_active_token() is None


def test_find_user_by_id_token():
    registry = TokenRegistry()
    registry.register("u1", {"idToken": "mytoken123"})
    registry.register("u2", {"idToken": "anothertoken"})
    found = registry.find_user_by_id_token("mytoken123")
    assert found == "u1"


def test_find_user_by_id_token_not_found():
    registry = TokenRegistry()
    registry.register("u1", {"idToken": "tok1"})
    assert registry.find_user_by_id_token("nosuchtoken") is None


def test_register_overwrites_existing():
    registry = TokenRegistry()
    registry.register("u1", {"idToken": "old"})
    registry.register("u1", {"idToken": "new"})
    assert registry.get("u1")["idToken"] == "new"


# ── TokenPersistence ───────────────────────────────────────────────────────


def test_write_and_read_json(tmp_path):
    p = TokenPersistence()
    path = tmp_path / "tok.json"
    data = {"userId": "u1", "idToken": "abc"}
    result = p.write_json(path, data)
    assert result is True
    loaded = p.read_json(path)
    assert loaded == data


def test_read_json_nonexistent_returns_none(tmp_path):
    p = TokenPersistence()
    path = tmp_path / "nofile.json"
    result = p.read_json(path)
    assert result is None


def test_read_json_invalid_json(tmp_path):
    p = TokenPersistence()
    path = tmp_path / "bad.json"
    path.write_text("not valid json {{{")
    result = p.read_json(path)
    assert result is None


def test_write_json_creates_parent_dirs(tmp_path):
    p = TokenPersistence()
    nested = tmp_path / "a" / "b" / "c" / "tok.json"
    result = p.write_json(nested, {"key": "val"})
    assert result is True
    assert nested.exists()


def test_static_read_write_roundtrip(tmp_path):
    path = tmp_path / "static.json"
    data = {"foo": "bar", "num": 42}
    TokenPersistence._write_json(path, data)
    loaded = TokenPersistence._read_json(path)
    assert loaded == data
