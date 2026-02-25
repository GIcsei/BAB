"""Tests for app.core.firestore_handler.Utils and DocumentKeyGenerator."""

import time

from app.core.firestore_handler.Utils import DocumentKeyGenerator, parse_to_firestore


def test_parse_true():
    result = parse_to_firestore("true")
    assert result == {"booleanValue": True}


def test_parse_false():
    result = parse_to_firestore("false")
    assert result == {"booleanValue": False}


def test_parse_true_case_insensitive():
    result = parse_to_firestore("TRUE")
    assert result == {"booleanValue": True}


def test_parse_integer():
    result = parse_to_firestore("42")
    assert result == {"integerValue": "42"}


def test_parse_negative_integer():
    result = parse_to_firestore("-7")
    assert result == {"integerValue": "-7"}


def test_parse_double():
    result = parse_to_firestore("3.14")
    assert result == {"doubleValue": 3.14}


def test_parse_negative_double():
    result = parse_to_firestore("-1.5")
    assert result == {"doubleValue": -1.5}


def test_parse_single_quoted_string():
    result = parse_to_firestore("'hello world'")
    assert result == {"stringValue": "hello world"}


def test_parse_double_quoted_string():
    result = parse_to_firestore('"foo bar"')
    assert result == {"stringValue": "foo bar"}


def test_parse_plain_string():
    result = parse_to_firestore("admin")
    assert result == {"stringValue": "admin"}


def test_parse_strips_whitespace():
    result = parse_to_firestore("  42  ")
    assert result == {"integerValue": "42"}


def test_parse_zero():
    result = parse_to_firestore("0")
    assert result == {"integerValue": "0"}


def test_generate_key_returns_20_chars():
    gen = DocumentKeyGenerator()
    key = gen.generate_key()
    assert len(key) == 20


def test_generate_key_unique():
    gen = DocumentKeyGenerator()
    keys = {gen.generate_key() for _ in range(10)}
    assert len(keys) == 10


def test_generate_key_only_valid_chars():
    gen = DocumentKeyGenerator()
    valid_chars = set(
        "-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz"
    )
    for _ in range(5):
        key = gen.generate_key()
        for c in key:
            assert c in valid_chars, f"Invalid char: {c!r} in key {key!r}"


def test_generate_key_duplicate_time(monkeypatch):
    gen = DocumentKeyGenerator()
    now_ms = int(time.time() * 1000)
    gen.last_push_time = now_ms
    gen.last_rand_chars = [0] * 12
    monkeypatch.setattr(
        "app.core.firestore_handler.Utils.time.time", lambda: now_ms / 1000.0
    )
    key = gen.generate_key()
    assert len(key) == 20


def test_generate_key_rollover(monkeypatch):
    gen = DocumentKeyGenerator()
    now_ms = int(time.time() * 1000)
    gen.last_push_time = now_ms
    gen.last_rand_chars = [63] + [0] * 11
    monkeypatch.setattr(
        "app.core.firestore_handler.Utils.time.time", lambda: now_ms / 1000.0
    )
    key = gen.generate_key()
    assert len(key) == 20
