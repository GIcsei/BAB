import logging
import os

from app.core.logging_config import (
    StructuredFormatter,
    TokenRedactingFilter,
    configure_logging,
)


def test_token_redacting_filter_redacts_tokens():
    filt = TokenRedactingFilter()
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Bearer token=abc123",
        args=(),
        exc_info=None,
    )
    assert filt.filter(record) is True
    assert record.getMessage() == "Bearer token=abc123"
    assert record.msg == "[REDACTED SENSITIVE DATA]"


def test_structured_formatter_json_includes_exception():
    fmt = StructuredFormatter(use_json=True)
    try:
        raise ValueError("boom")
    except ValueError as exc_info:  # type: ignore
        record = logging.LogRecord(
            name="app.test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="something failed",
            args=(),
            exc_info=exc_info.__traceback__,
        )
    import json

    output = fmt.format(record)
    data = json.loads(output)
    assert "exception" in data


def test_configure_logging_default(tmp_path):
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
    assert os.path.exists(log_file)


def test_configure_logging_json_mode(monkeypatch):
    monkeypatch.setenv("LOG_JSON", "true")
    configure_logging()


def test_configure_logging_idempotent():
    configure_logging()
    configure_logging()
