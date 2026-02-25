"""Tests for app.core.firestore_handler.QueryHandler – Firebase class methods."""

import json

import app.core.firestore_handler.QueryHandler as qh_mod
import pytest
from app.core.firestore_handler.QueryHandler import (
    Firebase,
    initialize_app,
)


@pytest.fixture(autouse=True)
def reset_firebase_singleton():
    """Save and restore the global Firebase singleton between tests."""
    original = qh_mod._DEFAULT_FIREBASE
    yield
    qh_mod._DEFAULT_FIREBASE = original


def _make_firebase(project_id="test-proj"):
    """Create a Firebase instance with a test config."""
    config = {"projectId": project_id}
    fb = Firebase(config)
    # api_key is used by auth_client and FirestoreService but not set in __init__
    fb.api_key = "test-api-key"
    return fb


# ── Firebase.__new__ / __init__ ────────────────────────────────────────────


def test_initialize_app_returns_firebase():
    fb = initialize_app({"projectId": "p1"})
    assert isinstance(fb, Firebase)
    assert fb.projectId == "p1"


def test_firebase_singleton_via_new():
    """Firebase() with no config returns the last initialized instance."""
    fb1 = initialize_app({"projectId": "proj1"})
    fb2 = Firebase()  # no config -> returns singleton
    assert fb1 is fb2


def test_firebase_init_idempotent():
    """Calling __init__ twice (via re-instantiation) is safe."""
    fb = initialize_app({"projectId": "proj2"})
    assert fb._initialized is True
    # second call should be a no-op
    fb.__init__({"projectId": "proj2"})
    assert fb.projectId == "proj2"


def test_firebase_no_singleton_raises():
    """Firebase() with no config when no singleton exists should raise."""
    qh_mod._DEFAULT_FIREBASE = None
    with pytest.raises(ValueError, match="Firebase not initialized"):
        Firebase()


# ── Firebase.save_login_token ──────────────────────────────────────────────


def test_save_login_token_no_token_file_raises():
    fb = initialize_app({"projectId": "p"})
    fb.token_service._token_file = None
    with pytest.raises(ValueError, match="TOKEN_FILE is not set"):
        fb.save_login_token({"idToken": "tok"})


def test_save_and_load_login_token(tmp_path):
    fb = initialize_app({"projectId": "p"})
    fb.token_service._token_file = tmp_path / "token.json"
    fb.save_login_token({"idToken": "abc", "refreshToken": "def"})
    loaded = fb.load_login_token()
    assert loaded["idToken"] == "abc"


def test_load_login_token_no_token_file():
    fb = initialize_app({"projectId": "p"})
    fb.token_service._token_file = None
    assert fb.load_login_token() is None


# ── Firebase.clear_token ───────────────────────────────────────────────────


def test_clear_token_removes_file(tmp_path):
    fb = initialize_app({"projectId": "p"})
    fb.token_service._token_file = tmp_path / "tok.json"
    fb.token_service._token_file.write_text('{"idToken": "x"}')
    fb.clear_token()
    assert not fb.token_service._token_file.exists()


def test_clear_token_no_file_noop(tmp_path):
    fb = initialize_app({"projectId": "p"})
    fb.token_service._token_file = tmp_path / "nonexistent.json"
    fb.clear_token()  # should not raise


# ── Firebase.register_user_tokens ─────────────────────────────────────────


def test_register_user_tokens(tmp_path):
    fb = initialize_app({"projectId": "p"})
    token = {"idToken": "tok", "refreshToken": "ref"}
    cred_path = tmp_path / "u1" / "credentials.json"
    cred_path.parent.mkdir(parents=True)

    fb.register_user_tokens("u1", token, credentials_path=cred_path)
    assert fb.token_service._registry.get("u1")["idToken"] == "tok"
    assert cred_path.exists()


def test_register_user_tokens_no_path():
    fb = initialize_app({"projectId": "p"})
    fb.register_user_tokens("u2", {"idToken": "t"}, credentials_path=None)
    assert fb.token_service._registry.get("u2")["idToken"] == "t"


# ── Firebase.get_user_token ────────────────────────────────────────────────


def test_get_user_token():
    fb = initialize_app({"projectId": "p"})
    fb.token_service._registry.register("u3", {"idToken": "xyz"})
    assert fb.get_user_token("u3")["idToken"] == "xyz"


def test_get_user_token_missing():
    fb = initialize_app({"projectId": "p"})
    assert fb.get_user_token("nobody") is None


# ── Firebase.set_active_user ───────────────────────────────────────────────


def test_set_active_user():
    fb = initialize_app({"projectId": "p"})
    fb.token_service._registry.register("u4", {"idToken": "t"})
    token = fb.set_active_user("u4")
    assert token["idToken"] == "t"


def test_set_active_user_missing_raises():
    fb = initialize_app({"projectId": "p"})
    with pytest.raises(ValueError, match="No token registered"):
        fb.set_active_user("nobody")


# ── Firebase.clear_user ────────────────────────────────────────────────────


def test_clear_user():
    fb = initialize_app({"projectId": "p"})
    fb.token_service._registry.register("u5", {"idToken": "t"})
    fb.clear_user("u5")
    assert fb.get_user_token("u5") is None


def test_clear_user_not_registered():
    fb = initialize_app({"projectId": "p"})
    fb.clear_user("ghost")  # should not raise


# ── Firebase.get_user_id_by_token ─────────────────────────────────────────


def test_get_user_id_by_token():
    fb = initialize_app({"projectId": "p"})
    fb.token_service._registry.register("u6", {"idToken": "unique_tok_789"})
    found = fb.get_user_id_by_token("unique_tok_789")
    assert found == "u6"


def test_get_user_id_by_token_not_found():
    fb = initialize_app({"projectId": "p"})
    assert fb.get_user_id_by_token("nosuchtoken") is None


# ── Firebase.verify_id_token in test mode ────────────────────────────────


def test_verify_id_token_returns_none_in_test_env():
    """In test mode, verify_id_token returns None without calling firebase-admin."""
    fb = initialize_app({"projectId": "p"})
    result = fb.verify_id_token("some_token")
    assert result is None


def test_verify_id_token_empty_token():
    fb = initialize_app({"projectId": "p"})
    assert fb.verify_id_token("") is None
    assert fb.verify_id_token(None) is None


# ── Firebase.database ─────────────────────────────────────────────────────


def test_database_returns_firestore_service():
    fb = _make_firebase()
    qh_mod._DEFAULT_FIREBASE = fb
    from app.core.firestore_handler.FirestoreService import FirestoreService

    db = fb.database()
    assert isinstance(db, FirestoreService)


def test_database_is_singleton():
    fb = _make_firebase()
    qh_mod._DEFAULT_FIREBASE = fb
    db1 = fb.database()
    db2 = fb.database()
    assert db1 is db2


# ── Firebase.load_tokens_from_dir ─────────────────────────────────────────


def test_load_tokens_from_dir_nonexistent(tmp_path):
    fb = _make_firebase()
    qh_mod._DEFAULT_FIREBASE = fb
    # Should not raise for nonexistent dir
    fb.load_tokens_from_dir(tmp_path / "nonexistent")


def test_load_tokens_from_dir_no_credentials(tmp_path):
    fb = _make_firebase()
    qh_mod._DEFAULT_FIREBASE = fb
    user_dir = tmp_path / "u1"
    user_dir.mkdir()
    # dir exists but no credentials.json -> should warn and skip
    fb.load_tokens_from_dir(tmp_path)
    assert fb.get_user_token("u1") is None


def test_load_tokens_from_dir_with_credentials(tmp_path):
    fb = _make_firebase()
    qh_mod._DEFAULT_FIREBASE = fb
    user_dir = tmp_path / "u1"
    user_dir.mkdir()
    cred = {"idToken": "tok", "userId": "u1", "email": "u@example.com"}
    (user_dir / "credentials.json").write_text(json.dumps(cred))

    # With refresh=False to avoid calling auth_client.refresh
    fb.load_tokens_from_dir(tmp_path, refresh=False)
    token = fb.get_user_token("u1")
    assert token is not None
    assert token["idToken"] == "tok"
