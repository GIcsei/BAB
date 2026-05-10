import logging
import os
import sys
from logging.handlers import RotatingFileHandler

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
    # After filtering, the message is redacted
    assert record.msg == "[REDACTED SENSITIVE DATA]"
    assert record.getMessage() == "[REDACTED SENSITIVE DATA]"


def test_token_redacting_filter_passes_safe_messages():
    filt = TokenRedactingFilter()
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Safe log message with no secrets",
        args=(),
        exc_info=None,
    )
    assert filt.filter(record) is True
    assert record.getMessage() == "Safe log message with no secrets"


def test_structured_formatter_json_includes_exception():
    fmt = StructuredFormatter(use_json=True)
    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="app.test",
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


def test_configure_logging_default(tmp_path):
    configure_logging()
    logger = logging.getLogger("app")
    assert logger.level in (logging.DEBUG, logging.INFO, logging.WARNING)


def test_configure_logging_with_log_file(tmp_path, monkeypatch):
    import app.core.config as cfg

    log_file = str(tmp_path / "test.log")
    monkeypatch.setenv("LOG_FILE", log_file)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    cfg._SETTINGS = None  # force re-read with new env vars
    try:
        configure_logging()
        logger = logging.getLogger("app")
        logger.info("test log entry")
        assert os.path.exists(log_file)
    finally:
        cfg._SETTINGS = None  # reset so other tests are not affected


def test_configure_logging_json_mode(monkeypatch):
    monkeypatch.setenv("LOG_JSON", "true")
    configure_logging()


def test_configure_logging_idempotent():
    configure_logging()
    configure_logging()


def test_configure_logging_with_env_rotation_values(tmp_path, monkeypatch):
    import app.core.config as cfg
    import app.core.logging_config as log_cfg

    log_file = str(tmp_path / "rotating.log")
    monkeypatch.setenv("LOG_FILE", log_file)
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("LOG_ROTATION_MAX_BYTES", "1024")
    monkeypatch.setenv("LOG_ROTATION_BACKUP_COUNT", "7")

    cfg._SETTINGS = None
    monkeypatch.setattr(log_cfg, "LOGGER_CONFIGURED", True)
    try:
        configure_logging()
        logger = logging.getLogger("app")
        rotating_handlers = [
            handler
            for handler in logger.handlers
            if isinstance(handler, RotatingFileHandler)
        ]
        assert rotating_handlers
        handler = rotating_handlers[0]
        assert handler.maxBytes == 1024
        assert handler.backupCount == 7
    finally:
        cfg._SETTINGS = None
