"""Extended DatabaseHandler tests – HTTP methods with mocked requests."""

from unittest.mock import MagicMock

import pytest

import app.core.firestore_handler.QueryHandler as qh_mod
from app.core.firestore_handler.QueryHandler import initialize_app


@pytest.fixture(autouse=True)
def setup_firebase_singleton():
    original = qh_mod._DEFAULT_FIREBASE
    fb = initialize_app({"projectId": "test-proj"})
    fb.api_key = "test-api-key"
    fb.requests = MagicMock()
    qh_mod._DEFAULT_FIREBASE = fb
    yield fb
    qh_mod._DEFAULT_FIREBASE = original


def _make_db():
    from app.core.firestore_handler.DatabaseHandler import Database

    return Database()


def _doc_resp(name="d1"):
    return {
        "name": f"projects/test-proj/databases/(default)/documents/{name}",
        "createTime": "2020-01-01T00:00:00Z",
        "updateTime": "2020-01-02T00:00:00Z",
        "fields": {"val": {"stringValue": "x"}},
    }


def _ok_resp(data):
    r = MagicMock()
    r.json.return_value = data
    r.raise_for_status = MagicMock()
    r.status_code = 200
    return r


# ── push ──────────────────────────────────────────────────────────────────


def test_push(setup_firebase_singleton):
    fb = setup_firebase_singleton
    fb.requests.post.return_value = _ok_resp({"name": "new_doc"})
    db = _make_db()
    db.child("messages")
    result = db.push({"text": "hello"}, token={"idToken": "tok"})
    assert result["name"] == "new_doc"


# ── set ───────────────────────────────────────────────────────────────────


def test_set(setup_firebase_singleton):
    fb = setup_firebase_singleton
    fb.requests.put.return_value = _ok_resp({"status": "set"})
    db = _make_db()
    db.child("col", "doc1")
    result = db.set({"key": "val"}, token={"idToken": "tok"})
    assert result["status"] == "set"


# ── update ────────────────────────────────────────────────────────────────


def test_update(setup_firebase_singleton):
    fb = setup_firebase_singleton
    fb.requests.patch.return_value = _ok_resp({"updated": True})
    db = _make_db()
    db.child("col", "doc1")
    result = db.update({"key": "new"}, token={"idToken": "tok"})
    assert result["updated"] is True


# ── remove ────────────────────────────────────────────────────────────────


def test_remove(setup_firebase_singleton):
    fb = setup_firebase_singleton
    fb.requests.delete.return_value = _ok_resp({})
    db = _make_db()
    db.child("col", "doc1")
    result = db.remove(token={"idToken": "tok"})
    assert result == {}


# ── _request – GET ────────────────────────────────────────────────────────


def test_request_get(setup_firebase_singleton):
    fb = setup_firebase_singleton
    doc = _doc_resp("mydoc")
    fb.requests.get.return_value = _ok_resp(doc)
    db = _make_db()
    db.child("col", "mydoc")
    result = db._request(token={"idToken": "tok"})
    assert result == doc


# ── _request – POST (StringQuery) ────────────────────────────────────────


def test_request_post_string_query(setup_firebase_singleton):
    fb = setup_firebase_singleton
    docs = [_doc_resp("q1")]
    fb.requests.post.return_value = _ok_resp(docs)
    db = _make_db()
    db.addStringQuery("status == 'sent'")
    result = db._request(token={"idToken": "tok"})
    assert result == docs
