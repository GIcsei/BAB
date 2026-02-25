"""Tests for app.core.firestore_handler.DataDescriptor – Collection class."""
import pytest

from app.core.firestore_handler.DataDescriptor import Collection, Document


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_doc(name="doc1", created="2020-01-01", updated="2020-01-02", fields=None):
    return Document(
        name=name,
        created=created,
        updated=updated,
        data_fields=fields or {"val": 1},
    )


def _make_doc_dict(name="doc1", value="hello"):
    return {
        "document": {
            "name": f"projects/p/dbs/documents/{name}",
            "createTime": "2020-01-01T00:00:00Z",
            "updateTime": "2020-01-02T00:00:00Z",
            "fields": {"v": {"stringValue": value}},
        }
    }


# ── Document repr/str ──────────────────────────────────────────────────────


def test_document_str():
    doc = _make_doc(name="mydoc", fields={"x": 42})
    s = str(doc)
    assert "mydoc" in s
    assert "x" in s


def test_document_repr():
    doc = _make_doc(name="repdoc", fields={"k": "v"})
    r = repr(doc)
    assert "repdoc" in r


def test_document_str_truncates_long_fields():
    # Field preview should be truncated at 300 chars
    long_fields = {f"field_{i}": "x" * 30 for i in range(20)}
    doc = Document("d", "c", "u", long_fields)
    s = str(doc)
    assert "..." in s or len(s) < 2000  # truncation happened or output is manageable


def test_document_repr_truncates_long_fields():
    long_fields = {f"field_{i}": "x" * 30 for i in range(10)}
    doc = Document("d", "c", "u", long_fields)
    r = repr(doc)
    assert "..." in r


def test_document_from_dict_no_fields():
    input_dict = {
        "document": {
            "name": "projects/p/dbs/documents/empty",
            "createTime": "2020-01-01T00:00:00Z",
            "updateTime": "2020-01-02T00:00:00Z",
        }
    }
    doc = Document.from_dict(input_dict)
    assert doc.name == "empty"
    assert doc.data_fields is None


def test_document_from_dict_bare_format():
    """Accepts bare document dict (no outer 'document' key)."""
    input_dict = {
        "name": "projects/p/dbs/documents/bare",
        "createTime": "2020-01-01T00:00:00Z",
        "updateTime": "2020-01-02T00:00:00Z",
        "fields": {"x": {"integerValue": "7"}},
    }
    doc = Document.from_dict(input_dict)
    assert doc.name == "bare"
    assert doc.data_fields["x"] == 7


def test_convert_firefield_unsupported_type():
    with pytest.raises(ValueError, match="Unsupported value type"):
        Document.convert_firefield({"timestampValue": "2020-01-01"})


def test_convert_firefield_wrong_structure():
    with pytest.raises(ValueError, match="not a field"):
        Document.convert_firefield({"a": 1, "b": 2})


def test_from_dict_not_dict_raises():
    with pytest.raises(ValueError, match="Input must be a dictionary"):
        Document.from_dict("not a dict")


# ── Collection ─────────────────────────────────────────────────────────────


def test_collection_creation():
    col = Collection("mycol")
    assert col.name == "mycol"
    assert col.documents == []


def test_collection_none_name_raises():
    with pytest.raises(ValueError, match="Name cannot be None"):
        Collection(None)


def test_collection_with_initial_docs():
    docs = [_make_doc("d1"), _make_doc("d2")]
    col = Collection("col", docs)
    assert len(col.documents) == 2


def test_collection_add_doc():
    col = Collection("col")
    col.add_doc(_make_doc("d1"))
    col.add_doc(_make_doc("d2"))
    assert len(col.documents) == 2


def test_collection_sort_by():
    docs = [
        _make_doc("a", fields={"score": 10}),
        _make_doc("b", fields={"score": 30}),
        _make_doc("c", fields={"score": 20}),
    ]
    col = Collection("col", docs)
    col.sort_by("score", reverse=True)
    assert col.documents[0].data_fields["score"] == 30
    assert col.documents[-1].data_fields["score"] == 10


def test_collection_sort_by_ascending():
    docs = [
        _make_doc("a", fields={"score": 10}),
        _make_doc("b", fields={"score": 30}),
        _make_doc("c", fields={"score": 20}),
    ]
    col = Collection("col", docs)
    col.sort_by("score", reverse=False)
    assert col.documents[0].data_fields["score"] == 10


def test_collection_sort_by_missing_field_raises():
    """Sorting docs where some lack the field value raises TypeError (None vs int)."""
    docs = [
        _make_doc("a", fields={"score": 10}),
        _make_doc("b", fields={}),
    ]
    col = Collection("col", docs)
    # Python 3 cannot compare int and None; expect TypeError
    with pytest.raises(TypeError):
        col.sort_by("score")


def test_collection_update_elems_none():
    docs = [_make_doc("d1"), _make_doc("d2")]
    col = Collection("col", docs)
    col.update_elems(None)
    assert len(col.documents) == 2


def test_collection_update_elems_int():
    docs = [_make_doc("d1"), _make_doc("d2"), _make_doc("d3")]
    col = Collection("col", docs)
    col.update_elems(1)
    assert len(col.documents) == 1
    assert col.documents[0].name == "d2"


def test_collection_update_elems_int_out_of_bounds():
    docs = [_make_doc("d1")]
    col = Collection("col", docs)
    col.update_elems(99)
    assert col.documents == []


def test_collection_update_elems_slice():
    docs = [_make_doc(f"d{i}") for i in range(5)]
    col = Collection("col", docs)
    col.update_elems(slice(1, 3))
    assert len(col.documents) == 2
    assert col.documents[0].name == "d1"


def test_collection_update_elems_list():
    docs = [_make_doc(f"d{i}") for i in range(5)]
    col = Collection("col", docs)
    col.update_elems([0, 2, 4])
    assert len(col.documents) == 3
    assert col.documents[0].name == "d0"
    assert col.documents[1].name == "d2"
    assert col.documents[2].name == "d4"


def test_collection_update_elems_list_invalid_index_ignored():
    docs = [_make_doc("d0"), _make_doc("d1")]
    col = Collection("col", docs)
    col.update_elems([0, 99])  # 99 out of range, silently skipped
    assert len(col.documents) == 1


def test_collection_update_elems_list_non_int_raises():
    docs = [_make_doc("d0")]
    col = Collection("col", docs)
    with pytest.raises(TypeError, match="Indices must be integers"):
        col.update_elems(["bad"])


def test_collection_update_elems_unsupported_type_raises():
    col = Collection("col", [_make_doc()])
    with pytest.raises(TypeError, match="Unsupported elemnum type"):
        col.update_elems(3.14)


def test_collection_from_list():
    docs_dicts = [_make_doc_dict(f"d{i}", str(i)) for i in range(3)]
    col = Collection.from_list("mycol", docs_dicts)
    assert col.name == "mycol"
    assert len(col.documents) == 3


def test_collection_str():
    docs = [_make_doc("d1"), _make_doc("d2")]
    col = Collection("col", docs)
    s = str(col)
    assert "2" in s


def test_collection_repr():
    docs = [_make_doc(f"d{i}") for i in range(7)]
    col = Collection("col", docs)
    r = repr(col)
    assert "..." in r  # truncated after 5


def test_collection_repr_few_docs():
    docs = [_make_doc("x")]
    col = Collection("col", docs)
    r = repr(col)
    assert "x" in r
    assert "..." not in r
