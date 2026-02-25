"""
Structured logging configuration with token redaction.
- Redact idToken, refreshToken, and password-like values
- JSON output for easier parsing (optional)
- Default LOG_LEVEL=INFO
"""

import json
import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict


class TokenRedactingFilter(logging.Filter):
    """Remove sensitive token/password values from log records."""

    SENSITIVE_PATTERNS = [
        (r'"idToken"\s*:\s*"([^"]+)"', '"idToken": "REDACTED"'),
        (r'"refreshToken"\s*:\s*"([^"]+)"', '"refreshToken": "REDACTED"'),
        (r'"password"\s*:\s*"([^"]+)"', '"password": "REDACTED"'),
        (r"Bearer\s+[a-zA-Z0-9_\-\.]+", "Bearer REDACTED"),
        (r"Authorization.*", "Authorization: REDACTED"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive data from log message and arguments."""
        if record.msg:
            msg_str = str(record.msg)
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                msg_str = re.sub(pattern, replacement, msg_str)
            record.msg = msg_str

        if record.args:
            if isinstance(record.args, dict):
                for key in list(record.args.keys()):
                    if any(
                        sensitive in key.lower()
                        for sensitive in ["token", "password", "secret", "key"]
                    ):
                        record.args[key] = "REDACTED"
            elif isinstance(record.args, tuple):
                redacted_args = []
                for arg in record.args:
                    if isinstance(arg, str):
                        for pattern, replacement in self.SENSITIVE_PATTERNS:
                            arg = re.sub(pattern, replacement, arg)
                    redacted_args.append(arg)
                record.args = tuple(redacted_args)

        return True


class StructuredFormatter(logging.Formatter):
    """Format logs as structured JSON (optional; falls back to text)."""

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
            # Plain text fallback
            return f"{self.formatTime(record)} {record.levelname} [{record.name}] {record.getMessage()}"


def configure_logging(use_json: bool = False) -> None:
    """
    Configure application logging.
    - LOG_LEVEL: env var, default INFO (was DEBUG)
    - LOG_FILE: optional file path; uses RotatingFileHandler
    - Redacts tokens, passwords, etc.
    - Logs to stdout if LOG_FILE not set (Docker-friendly)
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("LOG_FILE", "")
    use_json = os.getenv("LOG_JSON", "false").lower() in ("1", "true", "yes")

    project_logger = logging.getLogger("app")

    # Clear any existing handlers
    for handler in list(project_logger.handlers):
        project_logger.removeHandler(handler)

    level = getattr(logging, log_level, logging.INFO)
    project_logger.setLevel(level)

    # Add token redaction filter
    redact_filter = TokenRedactingFilter()

    # Formatter
    formatter = StructuredFormatter(use_json=use_json)

    # File handler (if LOG_FILE set)
    if log_file:
        try:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        fh = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        fh.addFilter(redact_filter)
        project_logger.addHandler(fh)

    # Stdout handler (always)
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(level)
    sh.setFormatter(formatter)
    sh.addFilter(redact_filter)
    project_logger.addHandler(sh)

    project_logger.propagate = False

    project_logger.info(
        "Logging configured: level=%s, file=%s, json=%s",
        log_level,
        log_file or "stdout",
        use_json,
    )
