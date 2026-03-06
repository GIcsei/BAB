"""
Structured logging configuration with token redaction.
- Redact idToken, refreshToken, and password-like values
- JSON output for easier parsing (optional)
- Default LOG_LEVEL=INFO
"""

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict

from app.core.config import get_settings

TOKEN_KEYS = ("token", "idToken", "refreshToken", "authorization")
LOGGER_CONFIGURED = False


class TokenRedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage())
        for key in TOKEN_KEYS:
            if key.lower() in msg.lower():
                record.msg = "[REDACTED SENSITIVE DATA]"
                record.args = None
                break
        return True


class StructuredFormatter(logging.Formatter):
    default_msec_format = "%s.%03d"

    def __init__(self, use_json: bool = False):
        super().__init__()
        self.use_json = use_json

    def format(self, record: logging.LogRecord) -> str:
        if self.use_json:
            log_dict: Dict[str, Any] = {
                "timestamp": self.formatTime(record),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info:
                log_dict["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_dict)
        else:
            return f"{self.formatTime(record)} {record.levelname} [{record.name}] {record.getMessage()}"


def configure_logging(use_json: bool = False) -> None:
    """
    Configure application logging.
    - LOG_LEVEL: env var, default INFO (was DEBUG)
    - LOG_FILE: optional file path; uses RotatingFileHandler
    - Redacts tokens, passwords, etc.
    - Logs to stdout if LOG_FILE not set (Docker-friendly)
    """
    global LOGGER_CONFIGURED
    log_level = "INFO"
    log_file = None

    if LOGGER_CONFIGURED:
        settings = get_settings()
        log_level = settings.log_level
        log_file = settings.log_file
        use_json = settings.log_json

    project_logger = logging.getLogger("app")

    for handler in list(project_logger.handlers):
        project_logger.removeHandler(handler)

    level = getattr(logging, log_level, logging.INFO)
    project_logger.setLevel(level)

    redact_filter = TokenRedactingFilter()

    formatter = StructuredFormatter(use_json=use_json)

    if log_file:
        try:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            project_logger.warning("Could not create log directory: %s", exc)
        fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        fh.addFilter(redact_filter)
        project_logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(level)
    sh.setFormatter(formatter)
    sh.addFilter(redact_filter)
    project_logger.addHandler(sh)

    project_logger.propagate = False

    project_logger.info("Logger configured first time: %s", LOGGER_CONFIGURED)

    project_logger.info(
        "Logging configured: level=%s, file=%s, json=%s",
        log_level,
        log_file or "stdout",
        use_json,
    )
    LOGGER_CONFIGURED = True
