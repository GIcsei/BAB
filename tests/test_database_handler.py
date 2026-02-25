"""Tests for app.core.firestore_handler.DatabaseHandler – Database class."""
from unittest.mock import MagicMock, patch

import pytest

import app.core.firestore_handler.QueryHandler as qh_mod
from app.core.firestore_handler.QueryHandler import Firebase, initialize_app


@pytest.fixture(autouse=True)
def setup_firebase_singleton():
    """Ensure a Firebase singleton with api_key exists before Database tests."""
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


# ── Database construction ──────────────────────────────────────────────────


def test_database_init():
    db = _make_db()
    assert db.path == ""
    assert db.build_query == {}


# ── Query builder methods ──────────────────────────────────────────────────


def test_order_by_key():
    db = _make_db()
    result = db.order_by_key()
    assert db.build_query["orderBy"] == "$key"
    assert result is db  # fluent interface


def test_order_by_value():
    db = _make_db()
    db.order_by_value()
    assert db.build_query["orderBy"] == "$value"


def test_order_by_field():
    db = _make_db()
    db.order_by_field("createdAt")
    assert db.build_query["orderBy"] == "createdAt"


def test_start_at():
    db = _make_db()
    db.start_at("val1")
    assert db.build_query["startAt"] == "val1"


def test_end_at():
    db = _make_db()
    db.end_at("val2")
    assert db.build_query["endAt"] == "val2"


def test_equal_to():
    db = _make_db()
    db.equal_to("xyz")
    assert db.build_query["equalTo"] == "xyz"


def test_limit_to_first():
    db = _make_db()
    db.limit_to_first(10)
    assert db.build_query["limitToFirst"] == 10


def test_limit_to_last():
    db = _make_db()
    db.limit_to_last(5)
    assert db.build_query["limitToLast"] == 5


def test_add_string_query():
    db = _make_db()
    db.addStringQuery("status == 'sent'")
    assert db.build_query["StringQuery"] == "status == 'sent'"
    assert db.path == ":runQuery"


def test_child():
    db = _make_db()
    db.child("messages", "user1")
    assert db.path == "/messages/user1"


def test_child_multiple_calls():
    db = _make_db()
    db.child("col").child("doc")
    assert db.path == "/col/doc"


# ── build_request_url ──────────────────────────────────────────────────────


def test_build_request_url_no_path():
    db = _make_db()
    url = db.build_request_url()
    assert "firestore.googleapis.com" in url
    assert "test-proj" in url


def test_build_request_url_with_path():
    db = _make_db()
    db.child("messages")
    url = db.build_request_url()
    assert "/messages" in url


def test_build_request_url_with_string_query_param():
    db = _make_db()
    db.build_query["orderBy"] = "field1"
    url = db.build_request_url()
    assert url is not None


def test_build_request_url_with_bool_query_param():
    db = _make_db()
    db.build_query["someFlag"] = True
    url = db.build_request_url()
    assert url is not None


# ── build_headers ──────────────────────────────────────────────────────────


def test_build_headers_no_token():
    db = _make_db()
    headers = db.build_headers()
    assert "content-type" in headers
    assert "Authorization" not in headers


def test_build_headers_with_token():
    db = _make_db()
    headers = db.build_headers({"idToken": "mytoken"})
    assert headers["Authorization"] == "Bearer mytoken"


# ── generate_key ───────────────────────────────────────────────────────────


def test_generate_key_returns_20_chars():
    db = _make_db()
    key = db.generate_key()
    assert len(key) == 20


def test_generate_key_unique():
    db = _make_db()
    keys = {db.generate_key() for _ in range(5)}
    # Should generate unique keys
    assert len(keys) >= 3  # some may collide if same ms, but most should be unique


def test_generate_key_duplicate_time():
    """Force the duplicate_time branch by pre-setting last_push_time."""
    import time

    db = _make_db()
    now_ms = int(time.time() * 1000)
    db.last_push_time = now_ms
    db.last_rand_chars = [0] * 12  # initialize for duplicate path

    import unittest.mock as mock

    with mock.patch("app.core.firestore_handler.DatabaseHandler.time") as mock_time:
        mock_time.time.return_value = now_ms / 1000.0
        mock_time.floor = lambda x: int(x)
        key = db.generate_key()
    assert len(key) == 20


# ── filtering ──────────────────────────────────────────────────────────────


def test_filtering_limit_to_first():
    from app.core.firestore_handler.DataDescriptor import Collection, Document

    docs = [
        Document(f"d{i}", "c", "u", {"val": i})
        for i in range(5)
    ]
    col = Collection("col", docs)
    db = _make_db()
    result = db.filtering(col, {"limitToFirst": 2})
    assert len(result.documents) == 2


def test_filtering_order_by():
    from app.core.firestore_handler.DataDescriptor import Collection, Document

    docs = [
        Document("d1", "c", "u", {"score": 10}),
        Document("d2", "c", "u", {"score": 30}),
        Document("d3", "c", "u", {"score": 20}),
    ]
    col = Collection("col", docs)
    db = _make_db()
    result = db.filtering(col, {"orderBy": "score"})
    assert result.documents[0].data_fields["score"] == 30


# ── listDocuments ─────────────────────────────────────────────────────────


def test_list_documents(setup_firebase_singleton):
    fb = setup_firebase_singleton
    fb.requests.get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"documents": []},
        raise_for_status=MagicMock(),
    )
    db = _make_db()
    result = db.listDocuments(token={"idToken": "tok"})
    assert result == {"documents": []}
