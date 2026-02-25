"""Tests for app.core.netbank.credentials – save/load/delete."""
import os
from pathlib import Path

import pytest

import app.core.netbank.credentials as creds_mod
from app.core.netbank.credentials import (
    delete_user_credentials,
    load_user_credentials,
    save_user_credentials,
)


# ── Helpers ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_credential_cache():
    """Ensure in-memory cache is clean before and after each test."""
    with creds_mod._CACHE_LOCK:
        creds_mod._CREDENTIAL_CACHE.clear()
    yield
    with creds_mod._CACHE_LOCK:
        creds_mod._CREDENTIAL_CACHE.clear()


# ── save_user_credentials ──────────────────────────────────────────────────


def test_save_requires_user_id(tmp_path):
    with pytest.raises(ValueError, match="user_id is required"):
        save_user_credentials("", "user", "12345", "pw", config_dir=str(tmp_path))


def test_save_creates_credential_file(tmp_path):
    save_user_credentials(
        user_id="u1",
        username="testuser",
        account_number="ACC001",
        password="p@ssw0rd",
        config_dir=str(tmp_path),
    )
    cred_path = creds_mod._cred_path_for_dir(str(tmp_path), "u1")
    assert os.path.exists(cred_path)


def test_save_populates_in_memory_cache(tmp_path):
    save_user_credentials(
        user_id="u2",
        username="alice",
        account_number="ACC002",
        password="secret",
        config_dir=str(tmp_path),
    )
    with creds_mod._CACHE_LOCK:
        cached = creds_mod._CREDENTIAL_CACHE.get("u2")
    assert cached is not None
    assert cached["username"] == "alice"
    assert cached["account_number"] == "ACC002"
    assert cached["password"] == "secret"


# ── load_user_credentials ──────────────────────────────────────────────────


def test_load_returns_none_for_empty_user_id():
    result = load_user_credentials("")
    assert result is None


def test_load_returns_none_when_no_file(tmp_path):
    result = load_user_credentials("ghost_user", config_dir=str(tmp_path))
    assert result is None


def test_load_from_cache(tmp_path):
    save_user_credentials(
        user_id="u3",
        username="bob",
        account_number="ACC003",
        password="hunter2",
        config_dir=str(tmp_path),
    )
    # Load from in-memory cache (no disk read)
    result = load_user_credentials("u3", config_dir=str(tmp_path))
    assert result is not None
    assert result["username"] == "bob"
    assert result["password"] == "hunter2"


def test_load_from_disk_after_cache_clear(tmp_path):
    save_user_credentials(
        user_id="u4",
        username="carol",
        account_number="ACC004",
        password="qwerty",
        config_dir=str(tmp_path),
    )
    # Clear cache to force disk load
    with creds_mod._CACHE_LOCK:
        creds_mod._CREDENTIAL_CACHE.clear()

    result = load_user_credentials("u4", config_dir=str(tmp_path))
    assert result is not None
    assert result["username"] == "carol"
    assert result["account_number"] == "ACC004"


def test_load_returns_copy_not_reference(tmp_path):
    save_user_credentials(
        user_id="u5",
        username="dave",
        account_number="ACC005",
        password="pass",
        config_dir=str(tmp_path),
    )
    r1 = load_user_credentials("u5", config_dir=str(tmp_path))
    r2 = load_user_credentials("u5", config_dir=str(tmp_path))
    r1["username"] = "modified"
    assert r2["username"] == "dave"


# ── delete_user_credentials ────────────────────────────────────────────────


def test_delete_empty_user_id():
    result = delete_user_credentials("")
    assert result is False


def test_delete_nonexistent_user(tmp_path):
    result = delete_user_credentials("no_such_user", config_dir=str(tmp_path))
    assert result is False


def test_delete_removes_file_and_cache(tmp_path):
    save_user_credentials(
        user_id="u6",
        username="eve",
        account_number="ACC006",
        password="delme",
        config_dir=str(tmp_path),
    )
    cred_path = creds_mod._cred_path_for_dir(str(tmp_path), "u6")
    assert os.path.exists(cred_path)

    result = delete_user_credentials("u6", config_dir=str(tmp_path))
    assert result is True
    assert not os.path.exists(cred_path)

    with creds_mod._CACHE_LOCK:
        assert "u6" not in creds_mod._CREDENTIAL_CACHE


def test_roundtrip_save_load_delete(tmp_path):
    uid = "roundtrip_user"
    save_user_credentials(
        user_id=uid,
        username="frank",
        account_number="ACC999",
        password="f@nk",
        config_dir=str(tmp_path),
    )
    # clear cache so disk is read
    with creds_mod._CACHE_LOCK:
        creds_mod._CREDENTIAL_CACHE.clear()

    loaded = load_user_credentials(uid, config_dir=str(tmp_path))
    assert loaded["username"] == "frank"
    assert loaded["password"] == "f@nk"

    deleted = delete_user_credentials(uid, config_dir=str(tmp_path))
    assert deleted is True

    after_delete = load_user_credentials(uid, config_dir=str(tmp_path))
    assert after_delete is None


def test_hash_tag_is_deterministic():
    h1 = creds_mod._hash_tag("some.tag")
    h2 = creds_mod._hash_tag("some.tag")
    assert h1 == h2
    assert len(h1) == 16
