"""Tests for app.core.firestore_handler.Query – FirestoreQueryBuilder."""
import pytest

from app.core.firestore_handler.Query import FirestoreQueryBuilder


# ── build_query – simple conditions ───────────────────────────────────────


def test_simple_equal_string():
    builder = FirestoreQueryBuilder("messages")
    query = builder.build_query("status == 'sent'")
    sq = query["structuredQuery"]
    assert sq["from"] == [{"collectionId": "messages"}]
    ff = sq["where"]["fieldFilter"]
    assert ff["field"]["fieldPath"] == "status"
    assert ff["op"] == "EQUAL"
    assert ff["value"] == {"stringValue": "sent"}


def test_simple_greater_than_int():
    builder = FirestoreQueryBuilder("items")
    query = builder.build_query("priority > 2")
    ff = query["structuredQuery"]["where"]["fieldFilter"]
    assert ff["op"] == "GREATER_THAN"
    assert ff["value"] == {"integerValue": "2"}


def test_simple_not_equal():
    builder = FirestoreQueryBuilder("col")
    query = builder.build_query("status != 'archived'")
    ff = query["structuredQuery"]["where"]["fieldFilter"]
    assert ff["op"] == "NOT_EQUAL"


def test_simple_less_than_or_equal():
    builder = FirestoreQueryBuilder("col")
    query = builder.build_query("count <= 100")
    ff = query["structuredQuery"]["where"]["fieldFilter"]
    assert ff["op"] == "LESS_THAN_OR_EQUAL"


def test_simple_greater_than_or_equal():
    builder = FirestoreQueryBuilder("col")
    query = builder.build_query("count >= 5")
    ff = query["structuredQuery"]["where"]["fieldFilter"]
    assert ff["op"] == "GREATER_THAN_OR_EQUAL"


def test_simple_less_than():
    builder = FirestoreQueryBuilder("col")
    query = builder.build_query("age < 18")
    ff = query["structuredQuery"]["where"]["fieldFilter"]
    assert ff["op"] == "LESS_THAN"


def test_boolean_value():
    builder = FirestoreQueryBuilder("col")
    query = builder.build_query("active == true")
    ff = query["structuredQuery"]["where"]["fieldFilter"]
    assert ff["value"] == {"booleanValue": True}


# ── build_query – AND / OR ─────────────────────────────────────────────────


def test_and_condition():
    builder = FirestoreQueryBuilder("col")
    query = builder.build_query("status == 'sent' AND priority > 2")
    where = query["structuredQuery"]["where"]
    assert "compositeFilter" in where
    cf = where["compositeFilter"]
    assert cf["op"] == "AND"
    assert len(cf["filters"]) == 2


def test_or_condition():
    builder = FirestoreQueryBuilder("col")
    query = builder.build_query("status == 'sent' OR archived == true")
    where = query["structuredQuery"]["where"]
    assert "compositeFilter" in where
    cf = where["compositeFilter"]
    assert cf["op"] == "OR"


# ── build_query – parentheses ──────────────────────────────────────────────


def test_parenthesized_and_or():
    builder = FirestoreQueryBuilder("messages")
    query = builder.build_query(
        "(status == 'sent' AND priority > 2) OR (archived == true AND owner == 'admin')"
    )
    where = query["structuredQuery"]["where"]
    # top-level OR
    assert where["compositeFilter"]["op"] == "OR"


# ── error cases ────────────────────────────────────────────────────────────


def test_empty_filter_raises():
    builder = FirestoreQueryBuilder("col")
    with pytest.raises(ValueError, match="Filter string is empty"):
        builder.build_query("")


def test_invalid_condition_raises():
    builder = FirestoreQueryBuilder("col")
    with pytest.raises(ValueError, match="Invalid condition format"):
        builder.build_query("invalidcondition")


# ── _parse_condition details ───────────────────────────────────────────────


def test_parse_condition_double_quoted():
    builder = FirestoreQueryBuilder("col")
    cond = builder._parse_condition('name == "alice"')
    assert cond["fieldFilter"]["value"] == {"stringValue": "alice"}


def test_parse_condition_numeric_double():
    builder = FirestoreQueryBuilder("col")
    cond = builder._parse_condition("score == 3.14")
    assert cond["fieldFilter"]["value"] == {"doubleValue": 3.14}
