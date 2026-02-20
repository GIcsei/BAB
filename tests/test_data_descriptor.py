import pytest

from app.core.firestore_handler.DataDescriptor import Document


def test_convert_firefield_string():
    assert Document.convert_firefield({"stringValue": "abc"}) == "abc"


def test_convert_firefield_integer_and_double():
    assert Document.convert_firefield({"integerValue": "42"}) == 42
    assert abs(Document.convert_firefield({"doubleValue": "3.14"}) - 3.14) < 1e-6


def test_convert_firefield_boolean_and_null():
    assert Document.convert_firefield({"booleanValue": "true"}) is True
    assert Document.convert_firefield({"booleanValue": False}) is False
    assert Document.convert_firefield({"nullValue": None}) is None


def test_from_dict_basic():
    input_dict = {
        "document": {
            "name": "projects/p/dbs/documents/mydoc",
            "createTime": "2020-01-01T00:00:00Z",
            "updateTime": "2020-01-02T00:00:00Z",
            "fields": {"f": {"stringValue": "v"}},
        }
    }
    doc = Document.from_dict(input_dict)
    assert doc.name == "mydoc"
    assert doc.data_fields["f"] == "v"


def test_from_dict_invalid_raises():
    with pytest.raises(ValueError):
        Document.from_dict({"invalid": "value"})
