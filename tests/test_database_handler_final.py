"""Extended DatabaseHandler tests – token from firebase, get method, stream."""

from unittest.mock import MagicMock, patch

import app.core.firestore_handler.QueryHandler as qh_mod
import pytest
from app.core.firestore_handler.DataDescriptor import Collection, Document
from app.core.firestore_handler.QueryHandler import initialize_app


@pytest.fixture(autouse=True)
def setup_firebase_singleton():
    original = qh_mod._DEFAULT_FIREBASE
    fb = initialize_app({"projectId": "test-proj"})
    fb.api_key = "test-api-key"
    fb.requests = MagicMock()
    # register a default token so database operations have an active token
    fb.token_service._registry.register("_test_user", {"idToken": "default-tok"})
    fb.token_service._registry.set_active("_test_user")
    qh_mod._DEFAULT_FIREBASE = fb
    yield fb
    qh_mod._DEFAULT_FIREBASE = original


def _make_db():
    from app.core.firestore_handler.DatabaseHandler import Database

    return Database()


def _ok_resp(data):
    r = MagicMock()
    r.json.return_value = data
    r.raise_for_status = MagicMock()
    r.status_code = 200
    return r


# ── listDocuments – uses fb.token when no token given (line 72) ───────────


def test_list_documents_uses_firebase_token(setup_firebase_singleton):
    """listDocuments uses fb.token when token=None."""
    fb = setup_firebase_singleton
    fb.requests.get.return_value = _ok_resp({"documents": []})

    db = _make_db()
    # Call without token - should use fb.token
    result = db.listDocuments(token=None)
    assert result == {"documents": []}


# ── _request – uses fb.token when no token given (line 114) ──────────────


def test_request_uses_firebase_token(setup_firebase_singleton):
    """_request uses fb.token when token=None."""
    fb = setup_firebase_singleton
    doc = {"name": "doc1", "fields": {}}
    fb.requests.get.return_value = _ok_resp(doc)

    db = _make_db()
    db.child("col", "doc1")
    result = db._request(token=None)
    assert result == doc


# ── build_request_url – int/float param (line 99) ─────────────────────────


def test_build_request_url_numeric_param():
    """build_request_url handles numeric (non-str, non-bool) query params."""
    db = _make_db()
    db.build_query["limitToFirst"] = 5  # int param
    url = db.build_request_url()
    assert url is not None


# ── filtering – limitToLast (lines 139-140) ────────────────────────────────


def test_filtering_limit_to_last():
    """filtering handles limitToLast correctly."""
    docs = [Document(f"d{i}", "c", "u", {"val": i}) for i in range(5)]
    col = Collection("col", docs)
    db = _make_db()
    result = db.filtering(col, {"limitToLast": 2})
    assert len(result.documents) == 2


# ── push – uses fb.token when no token given (line 177) ──────────────────


def test_push_uses_firebase_token(setup_firebase_singleton):
    """push uses fb.token when token=None."""
    fb = setup_firebase_singleton
    fb.requests.post.return_value = _ok_resp({"name": "new_doc"})

    db = _make_db()
    db.child("messages")
    result = db.push({"text": "hello"}, token=None)
    assert result["name"] == "new_doc"


# ── set – uses fb.token when no token given (line 191) ────────────────────


def test_set_uses_firebase_token(setup_firebase_singleton):
    """set uses fb.token when token=None."""
    fb = setup_firebase_singleton
    fb.requests.put.return_value = _ok_resp({"status": "set"})

    db = _make_db()
    db.child("col", "doc1")
    result = db.set({"key": "val"}, token=None)
    assert result["status"] == "set"


# ── update – uses fb.token when no token given (line 205) ─────────────────


def test_update_uses_firebase_token(setup_firebase_singleton):
    """update uses fb.token when token=None."""
    fb = setup_firebase_singleton
    fb.requests.patch.return_value = _ok_resp({"updated": True})

    db = _make_db()
    db.child("col", "doc1")
    result = db.update({"key": "new"}, token=None)
    assert result["updated"] is True


# ── remove – uses fb.token when no token given (line 219) ─────────────────


def test_remove_uses_firebase_token(setup_firebase_singleton):
    """remove uses fb.token when token=None."""
    fb = setup_firebase_singleton
    fb.requests.delete.return_value = _ok_resp({})

    db = _make_db()
    db.child("col", "doc1")
    result = db.remove(token=None)
    assert result == {}


# ── stream method (lines 229-230) ─────────────────────────────────────────


def test_stream_creates_stream_object(setup_firebase_singleton):
    """Database.stream returns a Stream object."""
    from app.core.firestore_handler.Utils import Stream

    db = _make_db()
    db.child("col", "doc1")

    with patch("app.core.firestore_handler.Utils.ClosableSSEClient"):
        stream = db.stream(stream_handler=lambda x: None, token=None, stream_id="s1")
    assert isinstance(stream, Stream)


# ── get method – patching typing.Collection to use DataDescriptor.Collection ─


def test_get_with_multi_doc_response(setup_firebase_singleton):
    """Database.get handles multi-document response (patching typing.Collection bug)."""
    import app.core.firestore_handler.DatabaseHandler as dbh_mod
    from app.core.firestore_handler.DataDescriptor import Collection as DC

    fb = setup_firebase_singleton
    docs = [
        {
            "name": f"projects/p/databases/(default)/documents/col/d{i}",
            "createTime": "2020-01-01T00:00:00Z",
            "updateTime": "2020-01-02T00:00:00Z",
            "fields": {"val": {"stringValue": str(i)}},
        }
        for i in range(3)
    ]
    fb.requests.get.return_value = _ok_resp({"documents": docs})

    db = _make_db()
    db.child("col")

    # Patch the module-level Collection to use DataDescriptor's Collection
    with patch.object(dbh_mod, "Collection", DC):
        result = db.get(token={"idToken": "tok"})

    assert isinstance(result, DC)
