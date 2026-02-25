"""Additional tests for credentials.py covering remaining error paths."""

import base64
import json
import os
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

import app.core.netbank.credentials as creds_mod
from app.core.netbank.credentials import (
    _CLASS_TAG,
    _cred_path_for_dir,
    _ensure_key,
    _key_path_for_dir,
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


# ── _ensure_key – fallback write path (lines 86-93) ──────────────────────


def test_ensure_key_fdopen_failure_falls_back_to_open(tmp_path, monkeypatch):
    """_ensure_key falls back to regular open() when os.fdopen fails."""
    monkeypatch.delenv("NETBANK_MASTER_KEY", raising=False)
    # Patch os.fdopen to fail ONLY the first call (key write)
    original_fdopen = os.fdopen
    call_count = [0]

    def failing_fdopen(fd, *args, **kwargs):
        call_count[0] += 1
        if call_count[0] <= 1:
            os.close(fd)
            raise OSError("fdopen failed")
        return original_fdopen(fd, *args, **kwargs)

    with patch("app.core.netbank.credentials.os.fdopen", side_effect=failing_fdopen):
        key = _ensure_key(str(tmp_path))

    assert isinstance(key, bytes)
    key_path = _key_path_for_dir(str(tmp_path))
    assert os.path.exists(key_path)


# ── save_user_credentials – default config dir (line 112) ─────────────────


def test_save_with_default_config_dir(tmp_path, monkeypatch):
    """save_user_credentials uses default config dir when none provided."""
    monkeypatch.setattr(creds_mod, "_DEFAULT_CONFIG_DIR", str(tmp_path))
    # Should not raise
    save_user_credentials("u1", "user", "ACC1", "pass")
    # Verify the file was created
    cred_path = _cred_path_for_dir(str(tmp_path), "u1")
    assert os.path.exists(cred_path)


# ── save_user_credentials – fdopen failure (lines 140-147) ────────────────


def test_save_fdopen_failure_falls_back_to_open(tmp_path, monkeypatch):
    """save_user_credentials falls back to regular open() when os.fdopen fails."""
    original_fdopen = os.fdopen
    call_count = [0]

    def failing_fdopen(fd, *args, **kwargs):
        call_count[0] += 1
        # Fail the credential write (not the key write)
        if call_count[0] == 2:  # second call: cred write
            os.close(fd)
            raise OSError("fdopen failed")
        return original_fdopen(fd, *args, **kwargs)

    with patch("app.core.netbank.credentials.os.fdopen", side_effect=failing_fdopen):
        # Should succeed via fallback path
        save_user_credentials("u1", "user", "ACC1", "pass", config_dir=str(tmp_path))

    cred_path = _cred_path_for_dir(str(tmp_path), "u1")
    assert os.path.exists(cred_path)


# ── load_user_credentials – default config dir (line 177) ─────────────────


def test_load_with_default_config_dir_returns_none(tmp_path, monkeypatch):
    """load_user_credentials returns None when user file doesn't exist in default dir."""
    monkeypatch.setattr(creds_mod, "_DEFAULT_CONFIG_DIR", str(tmp_path))
    result = load_user_credentials("nonexistent_user")
    assert result is None


# ── load_user_credentials – _ensure_key raises (lines 214-216) ────────────


def test_load_ensure_key_failure_returns_none(tmp_path):
    """load_user_credentials returns None if key derivation fails."""
    uid = "key_fail_user"
    cred_path = _cred_path_for_dir(str(tmp_path), uid)

    # Write a valid-looking cred file with valid class/user_id/token
    from cryptography.fernet import Fernet

    real_key = Fernet.generate_key()
    f = Fernet(real_key)
    payload = json.dumps(
        {
            "class": _CLASS_TAG,
            "user_id": uid,
            "username": "x",
            "account_number": "a",
            "password": "p",
        }
    )
    token = f.encrypt(payload.encode())
    token_b64 = base64.urlsafe_b64encode(token).decode()
    blob = {"class": _CLASS_TAG, "user_id": uid, "token": token_b64}
    os.makedirs(os.path.dirname(cred_path), exist_ok=True)
    with open(cred_path, "w") as fh:
        json.dump(blob, fh)

    with patch(
        "app.core.netbank.credentials._ensure_key", side_effect=RuntimeError("key fail")
    ):
        result = load_user_credentials(uid, config_dir=str(tmp_path))

    assert result is None


# ── load_user_credentials – generic decrypt exception (lines 227-229) ─────


def test_load_generic_decrypt_exception_returns_none(tmp_path):
    """load_user_credentials returns None on generic Fernet decrypt error."""
    uid = "generic_exc_user"
    cred_path = _cred_path_for_dir(str(tmp_path), uid)

    # Write a valid JSON blob with valid class/user_id
    key = Fernet.generate_key()
    f = Fernet(key)
    token = f.encrypt(b"some_payload")
    token_b64 = base64.urlsafe_b64encode(token).decode()
    blob = {"class": _CLASS_TAG, "user_id": uid, "token": token_b64}
    os.makedirs(os.path.dirname(cred_path), exist_ok=True)
    with open(cred_path, "w") as fh:
        json.dump(blob, fh)

    # Patch Fernet.decrypt to raise a generic exception (not InvalidToken)
    with (
        patch("app.core.netbank.credentials._ensure_key", return_value=key),
        patch(
            "app.core.netbank.credentials.Fernet.decrypt", side_effect=ValueError("bad")
        ),
    ):
        result = load_user_credentials(uid, config_dir=str(tmp_path))

    assert result is None


# ── load_user_credentials – decrypted payload tag mismatch (lines 234-235) ──


def test_load_decrypted_payload_tag_mismatch(tmp_path):
    """load_user_credentials returns None when decrypted payload has wrong class tag."""
    uid = "tag_mismatch_user"
    cred_path = _cred_path_for_dir(str(tmp_path), uid)

    key = Fernet.generate_key()
    f = Fernet(key)
    # Encrypt payload with wrong class tag inside
    payload = json.dumps(
        {
            "class": "WrongClass",
            "user_id": uid,
            "username": "u",
            "account_number": "a",
            "password": "p",
        }
    ).encode()
    token = f.encrypt(payload)
    token_b64 = base64.urlsafe_b64encode(token).decode()

    blob = {"class": _CLASS_TAG, "user_id": uid, "token": token_b64}
    os.makedirs(os.path.dirname(cred_path), exist_ok=True)
    with open(cred_path, "w") as fh:
        json.dump(blob, fh)

    with patch("app.core.netbank.credentials._ensure_key", return_value=key):
        result = load_user_credentials(uid, config_dir=str(tmp_path))

    assert result is None


# ── load_user_credentials – JSON parse error (lines 248-252) ─────────────


def test_load_json_parse_error_after_decrypt(tmp_path):
    """load_user_credentials returns None if decrypted payload isn't valid JSON."""
    uid = "json_err_user"
    cred_path = _cred_path_for_dir(str(tmp_path), uid)

    key = Fernet.generate_key()
    f = Fernet(key)
    # Encrypt non-JSON payload
    token = f.encrypt(b"not valid json {{{{")
    token_b64 = base64.urlsafe_b64encode(token).decode()

    blob = {"class": _CLASS_TAG, "user_id": uid, "token": token_b64}
    os.makedirs(os.path.dirname(cred_path), exist_ok=True)
    with open(cred_path, "w") as fh:
        json.dump(blob, fh)

    with patch("app.core.netbank.credentials._ensure_key", return_value=key):
        result = load_user_credentials(uid, config_dir=str(tmp_path))

    assert result is None


# ── delete_user_credentials – default config dir (line 263) ──────────────


def test_delete_with_default_config_dir(tmp_path, monkeypatch):
    """delete_user_credentials works with default config dir."""
    monkeypatch.setattr(creds_mod, "_DEFAULT_CONFIG_DIR", str(tmp_path))
    save_user_credentials("u_del", "user", "ACC1", "pw", config_dir=str(tmp_path))
    with creds_mod._CACHE_LOCK:
        creds_mod._CREDENTIAL_CACHE.clear()

    result = delete_user_credentials("u_del")
    assert result is True
