"""Tests for app.core.firestore_handler.FirestoreService with mocked requests."""

from unittest.mock import MagicMock

from app.core.firestore_handler.DataDescriptor import Collection
from app.core.firestore_handler.FirestoreService import (
    FirestoreService,
)


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


def test_build_headers_without_token():
    svc = FirestoreService(_make_firebase())
    headers = svc._build_headers()
    assert "Content-Type" in headers
    assert "Authorization" not in headers


def test_build_headers_with_token():
    svc = FirestoreService(_make_firebase())
    headers = svc._build_headers({"idToken": "mytoken"})
    assert headers["Authorization"] == "Bearer mytoken"


def test_build_url_regular_path():
    svc = FirestoreService(_make_firebase())
    url = svc._build_url("users/alice")
    assert url.endswith("/users/alice")


def test_build_url_with_leading_slash():
    svc = FirestoreService(_make_firebase())
    url = svc._build_url("/users/bob")
    assert "/users/bob" in url
    assert not url.split("documents")[1].startswith("//")


def test_build_url_runquery():
    svc = FirestoreService(_make_firebase())
    url = svc._build_url("runQuery")
    assert url.endswith(":runQuery")


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
    fb = _make_firebase()
    docs = [_document_response(f"d{i}") for i in range(3)]
    fb.requests.get.return_value = _ok_response(docs)
    svc = FirestoreService(fb)
    result = svc.get_document("col")
    assert isinstance(result, Collection)


def test_set_document():
    fb = _make_firebase()
    fb.requests.put.return_value = _ok_response({"status": "ok"})
    svc = FirestoreService(fb)
    result = svc.set_document("col/doc1", {"key": "value"})
    assert result == {"status": "ok"}
    fb.requests.put.assert_called_once()


def test_update_document():
    fb = _make_firebase()
    fb.requests.patch.return_value = _ok_response({"updated": True})
    svc = FirestoreService(fb)
    result = svc.update_document("col/doc1", {"field": "new"})
    assert result == {"updated": True}


def test_delete_document():
    fb = _make_firebase()
    fb.requests.delete.return_value = _ok_response({})
    svc = FirestoreService(fb)
    result = svc.delete_document("col/doc1")
    assert result == {}


def test_create_document():
    fb = _make_firebase()
    new_doc = _document_response("newdoc")
    fb.requests.post.return_value = _ok_response(new_doc)
    svc = FirestoreService(fb)
    result = svc.create_document("col", {"name": "newdoc"})
    assert result == new_doc


def test_run_query_returns_collection():
    fb = _make_firebase()
    docs = [_document_response("q1")]
    fb.requests.post.return_value = _ok_response(docs)
    svc = FirestoreService(fb)
    result = svc.run_query("col", "select *")
    assert isinstance(result, Collection)
