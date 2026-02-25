"""Tests for app.core.firestore_handler.FirestoreService with mocked requests."""
import json
from unittest.mock import MagicMock

import pytest

from app.core.firestore_handler.FirestoreService import FirestoreService, deserialize_response
from app.core.firestore_handler.DataDescriptor import Collection, Document


def _make_firebase(project_id="test-project"):
    fb = MagicMock()
    fb.projectId = project_id
    fb.api_key = "test-api-key"
    fb.requests = MagicMock()
    return fb


def _document_response(name="doc1", fields=None):
    return {
        "name": f"projects/test-project/databases/(default)/documents/{name}",
        "createTime": "2020-01-01T00:00:00Z",
        "updateTime": "2020-01-02T00:00:00Z",
        "fields": fields or {"key": {"stringValue": "val"}},
    }


def _ok_response(data):
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    resp.status_code = 200
    return resp


# ── _build_headers ─────────────────────────────────────────────────────────


def test_build_headers_without_token():
    svc = FirestoreService(_make_firebase())
    headers = svc._build_headers()
    assert "Content-Type" in headers
    assert "Authorization" not in headers


def test_build_headers_with_token():
    svc = FirestoreService(_make_firebase())
    headers = svc._build_headers({"idToken": "mytoken"})
    assert headers["Authorization"] == "Bearer mytoken"


# ── _build_url ─────────────────────────────────────────────────────────────


def test_build_url_regular_path():
    svc = FirestoreService(_make_firebase())
    url = svc._build_url("users/alice")
    assert url.endswith("/users/alice")


def test_build_url_with_leading_slash():
    svc = FirestoreService(_make_firebase())
    url = svc._build_url("/users/bob")
    assert "/users/bob" in url
    # should strip leading slash
    assert not url.split("documents")[1].startswith("//")


def test_build_url_runquery():
    svc = FirestoreService(_make_firebase())
    url = svc._build_url("runQuery")
    assert url.endswith(":runQuery")


# ── get_document ───────────────────────────────────────────────────────────


def test_get_document_returns_collection():
    fb = _make_firebase()
    doc_data = _document_response("mydoc")
    fb.requests.get.return_value = _ok_response(doc_data)

    svc = FirestoreService(fb)
    result = svc.get_document("users/alice")
    assert isinstance(result, Collection)
    assert len(result.documents) == 1
    assert result.documents[0].name == "mydoc"


def test_get_document_with_token():
    fb = _make_firebase()
    fb.requests.get.return_value = _ok_response(_document_response("doc2"))
    svc = FirestoreService(fb)
    result = svc.get_document("col/doc2", token={"idToken": "tok"})
    assert isinstance(result, Collection)


def test_get_document_list_response():
    """When API returns a list of documents, wrap in 'documents' key."""
    fb = _make_firebase()
    docs = [_document_response(f"d{i}") for i in range(3)]
    fb.requests.get.return_value = _ok_response(docs)
    svc = FirestoreService(fb)
    result = svc.get_document("col")
    assert isinstance(result, Collection)


# ── set_document ───────────────────────────────────────────────────────────


def test_set_document():
    fb = _make_firebase()
    fb.requests.put.return_value = _ok_response({"status": "ok"})
    svc = FirestoreService(fb)
    result = svc.set_document("col/doc1", {"key": "value"})
    assert result == {"status": "ok"}
    fb.requests.put.assert_called_once()


# ── update_document ────────────────────────────────────────────────────────


def test_update_document():
    fb = _make_firebase()
    fb.requests.patch.return_value = _ok_response({"updated": True})
    svc = FirestoreService(fb)
    result = svc.update_document("col/doc1", {"field": "new"})
    assert result == {"updated": True}


# ── delete_document ────────────────────────────────────────────────────────


def test_delete_document():
    fb = _make_firebase()
    fb.requests.delete.return_value = _ok_response({})
    svc = FirestoreService(fb)
    result = svc.delete_document("col/doc1")
    assert result == {}


# ── create_document ────────────────────────────────────────────────────────


def test_create_document():
    fb = _make_firebase()
    new_doc = _document_response("newdoc")
    fb.requests.post.return_value = _ok_response(new_doc)
    svc = FirestoreService(fb)
    result = svc.create_document("col", {"name": "newdoc"})
    assert result == new_doc


# ── run_query ─────────────────────────────────────────────────────────────


def test_run_query_returns_collection():
    fb = _make_firebase()
    docs = [_document_response("q1")]
    fb.requests.post.return_value = _ok_response(docs)
    svc = FirestoreService(fb)
    result = svc.run_query("messages", "status == 'sent'")
    assert isinstance(result, Collection)


# ── deserialize_response decorator ────────────────────────────────────────


def test_deserialize_response_with_empty_doc():
    """When response has no 'documents', wraps result as single Document."""
    doc_resp = _document_response("solo")

    @deserialize_response
    def mock_fn(*args, **kwargs):
        return doc_resp

    result = mock_fn()
    assert isinstance(result, Collection)
    assert result.documents[0].name == "solo"
