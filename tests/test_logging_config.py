"""Tests for app.core.logging_config."""

import logging
import os

from app.core.logging_config import (
    StructuredFormatter,
    TokenRedactingFilter,
    configure_logging,
)

# ── TokenRedactingFilter ───────────────────────────────────────────────────


def _make_record(msg, args=None):
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=msg,
        args=args or (),
        exc_info=None,
    )
    return record


def test_redact_filter_idtoken():
    f = TokenRedactingFilter()
    record = _make_record('Got token {"idToken": "abc123secret"}')
    f.filter(record)
    assert "abc123secret" not in str(record.msg)
    assert "REDACTED" in str(record.msg)


def test_redact_filter_refresh_token():
    f = TokenRedactingFilter()
    record = _make_record('{"refreshToken": "myRefreshValue"}')
    f.filter(record)
    assert "myRefreshValue" not in str(record.msg)
    assert "REDACTED" in str(record.msg)


def test_redact_filter_password():
    f = TokenRedactingFilter()
    record = _make_record('{"password": "s3cr3t"}')
    f.filter(record)
    assert "s3cr3t" not in str(record.msg)
    assert "REDACTED" in str(record.msg)


def test_redact_filter_bearer():
    f = TokenRedactingFilter()
    record = _make_record("Authorization: Bearer eyJhbGciOiJSUzI1NiJ9.payload.sig")
    f.filter(record)
    assert "eyJhbGciOiJSUzI1NiJ9" not in str(record.msg)
    assert "REDACTED" in str(record.msg)


def test_redact_filter_no_sensitive_data():
    f = TokenRedactingFilter()
    record = _make_record("Hello world, no secrets here")
    result = f.filter(record)
    assert result is True
    assert record.msg == "Hello world, no secrets here"


def test_redact_filter_returns_true():
    f = TokenRedactingFilter()
    record = _make_record("plain message")
    assert f.filter(record) is True


def test_redact_filter_tuple_args():
    f = TokenRedactingFilter()
    record = _make_record("user %s token %s", args=("alice", "Bearer secrettoken"))
    f.filter(record)
    args_str = str(record.args)
    assert "secrettoken" not in args_str


def test_redact_filter_dict_args():
    f = TokenRedactingFilter()
    record = _make_record(
        "login",
        args={"token": "supersecret", "user": "alice"},
    )
    f.filter(record)
    # dict args: sensitive keys should be redacted
    assert record.args.get("token") == "REDACTED"
    # non-sensitive preserved
    assert record.args.get("user") == "alice"


# ── StructuredFormatter ────────────────────────────────────────────────────


def test_structured_formatter_plain_text():
    fmt = StructuredFormatter(use_json=False)
    record = _make_record("hello")
    output = fmt.format(record)
    assert "hello" in output
    assert "INFO" in output


def test_structured_formatter_json():
    fmt = StructuredFormatter(use_json=True)
    record = _make_record("json message")
    import json

    output = fmt.format(record)
    data = json.loads(output)
    assert data["message"] == "json message"
    assert data["level"] == "INFO"
    assert "timestamp" in data
    assert "logger" in data


def test_structured_formatter_json_with_exception():
    fmt = StructuredFormatter(use_json=True)
    try:
        raise ValueError("test error")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test",
        level=logging.ERROR,
        pathname="",
        lineno=0,
        msg="something failed",
        args=(),
        exc_info=exc_info,
    )
    import json

    output = fmt.format(record)
    data = json.loads(output)
    assert "exception" in data


# ── configure_logging ──────────────────────────────────────────────────────


def test_configure_logging_default(tmp_path):
    # ensure no error is raised and the project logger is configured
    configure_logging()
    logger = logging.getLogger("app")
    assert logger.level in (logging.DEBUG, logging.INFO, logging.WARNING)


def test_configure_logging_with_log_file(tmp_path, monkeypatch):
    log_file = str(tmp_path / "test.log")
    monkeypatch.setenv("LOG_FILE", log_file)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    configure_logging()
    logger = logging.getLogger("app")
    logger.info("test log entry")
    # verify log file was created
    assert os.path.exists(log_file)


def test_configure_logging_json_mode(monkeypatch):
    monkeypatch.setenv("LOG_JSON", "true")
    configure_logging()
    # just ensure no exception


def test_configure_logging_idempotent():
    configure_logging()
    configure_logging()  # second call should not raise
