"""Extended credentials tests – error paths and edge cases."""

import base64
import json
import os
from unittest.mock import patch

import app.core.netbank.credentials as creds_mod
import pytest
from app.core.netbank.credentials import (
    _cred_path_for_dir,
    _ensure_key,
    delete_user_credentials,
    load_user_credentials,
    save_user_credentials,
)


@pytest.fixture(autouse=True)
def clear_cache():
    with creds_mod._CACHE_LOCK:
        creds_mod._CREDENTIAL_CACHE.clear()
    yield
    with creds_mod._CACHE_LOCK:
        creds_mod._CREDENTIAL_CACHE.clear()


# ── _ensure_key with NETBANK_MASTER_KEY ───────────────────────────────────


def test_ensure_key_with_valid_fernet_master_key(tmp_path, monkeypatch):
    """NETBANK_MASTER_KEY that is a valid Fernet key should be used directly."""
    from cryptography.fernet import Fernet

    valid_key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setenv("NETBANK_MASTER_KEY", valid_key)
    key = _ensure_key(str(tmp_path))
    assert key == valid_key.encode("utf-8")


def test_ensure_key_with_plaintext_master_key(tmp_path, monkeypatch):
    """NETBANK_MASTER_KEY that is NOT a valid Fernet key is hashed to create one."""
    monkeypatch.setenv("NETBANK_MASTER_KEY", "my_plain_text_secret_key")
    key = _ensure_key(str(tmp_path))
    # Should be a base64-encoded 32-byte key
    assert len(base64.urlsafe_b64decode(key)) == 32


def test_ensure_key_creates_new_key(tmp_path, monkeypatch):
    """_ensure_key creates a new key file if one doesn't exist."""
    monkeypatch.delenv("NETBANK_MASTER_KEY", raising=False)
    key = _ensure_key(str(tmp_path))
    assert isinstance(key, bytes)
    # Key file should have been created
    key_path = creds_mod._key_path_for_dir(str(tmp_path))
    assert os.path.exists(key_path)


def test_ensure_key_reads_existing_key(tmp_path, monkeypatch):
    """_ensure_key returns existing key if file exists."""
    monkeypatch.delenv("NETBANK_MASTER_KEY", raising=False)
    # Create key first time
    key1 = _ensure_key(str(tmp_path))
    # Second call should return the same key
    key2 = _ensure_key(str(tmp_path))
    assert key1 == key2


# ── load_user_credentials – error paths ───────────────────────────────────


def test_load_corrupted_json(tmp_path):
    """load_user_credentials returns None for corrupted JSON file."""
    uid = "corrupt_user"
    cred_path = _cred_path_for_dir(str(tmp_path), uid)
    os.makedirs(tmp_path, exist_ok=True)
    with open(cred_path, "w") as f:
        f.write("not valid json {{{")

    result = load_user_credentials(uid, config_dir=str(tmp_path))
    assert result is None


def test_load_tag_mismatch(tmp_path):
    """load_user_credentials returns None if class tag doesn't match."""
    uid = "tag_user"
    cred_path = _cred_path_for_dir(str(tmp_path), uid)
    os.makedirs(tmp_path, exist_ok=True)
    bad_blob = {"class": "wrong.tag", "user_id": uid, "token": "tok"}
    with open(cred_path, "w") as f:
        json.dump(bad_blob, f)

    result = load_user_credentials(uid, config_dir=str(tmp_path))
    assert result is None


def test_load_user_id_mismatch(tmp_path):
    """load_user_credentials returns None if user_id in file doesn't match."""
    uid = "right_user"
    cred_path = _cred_path_for_dir(str(tmp_path), uid)
    os.makedirs(tmp_path, exist_ok=True)
    bad_blob = {"class": creds_mod._CLASS_TAG, "user_id": "wrong_user", "token": "tok"}
    with open(cred_path, "w") as f:
        json.dump(bad_blob, f)

    result = load_user_credentials(uid, config_dir=str(tmp_path))
    assert result is None


def test_load_missing_token(tmp_path):
    """load_user_credentials returns None if token field is absent."""
    uid = "no_token_user"
    cred_path = _cred_path_for_dir(str(tmp_path), uid)
    os.makedirs(tmp_path, exist_ok=True)
    bad_blob = {"class": creds_mod._CLASS_TAG, "user_id": uid}  # no token
    with open(cred_path, "w") as f:
        json.dump(bad_blob, f)

    result = load_user_credentials(uid, config_dir=str(tmp_path))
    assert result is None


def test_load_invalid_base64_token(tmp_path):
    """load_user_credentials returns None for invalid base64-encoded token."""
    uid = "bad_b64_user"
    cred_path = _cred_path_for_dir(str(tmp_path), uid)
    os.makedirs(tmp_path, exist_ok=True)
    bad_blob = {
        "class": creds_mod._CLASS_TAG,
        "user_id": uid,
        "token": "!!!not base64!!!",
    }
    with open(cred_path, "w") as f:
        json.dump(bad_blob, f)

    result = load_user_credentials(uid, config_dir=str(tmp_path))
    assert result is None


def test_load_invalid_fernet_token(tmp_path, monkeypatch):
    """load_user_credentials returns None for cryptographically invalid token."""
    monkeypatch.delenv("NETBANK_MASTER_KEY", raising=False)
    uid = "bad_fernet_user"
    cred_path = _cred_path_for_dir(str(tmp_path), uid)
    os.makedirs(tmp_path, exist_ok=True)

    # Base64-encode some garbage that is not a valid Fernet token
    garbage_token = base64.urlsafe_b64encode(b"garbage_bytes_not_fernet").decode()
    blob = {
        "class": creds_mod._CLASS_TAG,
        "user_id": uid,
        "token": garbage_token,
    }
    with open(cred_path, "w") as f:
        json.dump(blob, f)

    result = load_user_credentials(uid, config_dir=str(tmp_path))
    assert result is None


# ── delete_user_credentials – exception handling ──────────────────────────


def test_delete_handles_oserror(tmp_path):
    """delete_user_credentials returns False if file removal fails."""
    uid = "del_fail_user"
    save_user_credentials(
        user_id=uid,
        username="x",
        account_number="y",
        password="z",
        config_dir=str(tmp_path),
    )
    # Clear cache so it must access disk
    with creds_mod._CACHE_LOCK:
        creds_mod._CREDENTIAL_CACHE.clear()

    with patch("os.remove", side_effect=OSError("permission denied")):
        result = delete_user_credentials(uid, config_dir=str(tmp_path))
    # Returns False when exception occurs
    assert result is False
