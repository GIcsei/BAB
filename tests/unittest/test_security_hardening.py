"""Tests for security hardening measures."""

import logging
import os

import pytest


class TestSensitiveKeyRedaction:
    """Verify extended logging redaction."""

    def test_redacts_password(self):
        from app.core.logging_config import TokenRedactingFilter

        filt = TokenRedactingFilter()
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="user password=secret123",
            args=(),
            exc_info=None,
        )
        filt.filter(record)
        assert record.msg == "[REDACTED SENSITIVE DATA]"

    def test_redacts_api_key(self):
        from app.core.logging_config import TokenRedactingFilter

        filt = TokenRedactingFilter()
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="using api_key=ABCD1234",
            args=(),
            exc_info=None,
        )
        filt.filter(record)
        assert record.msg == "[REDACTED SENSITIVE DATA]"

    def test_redacts_credential(self):
        from app.core.logging_config import TokenRedactingFilter

        filt = TokenRedactingFilter()
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="loaded credential from file",
            args=(),
            exc_info=None,
        )
        filt.filter(record)
        assert record.msg == "[REDACTED SENSITIVE DATA]"

    def test_redacts_private_key(self):
        from app.core.logging_config import TokenRedactingFilter

        filt = TokenRedactingFilter()
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="private_key loaded",
            args=(),
            exc_info=None,
        )
        filt.filter(record)
        assert record.msg == "[REDACTED SENSITIVE DATA]"

    def test_backward_compat_token_keys_alias(self):
        from app.core.logging_config import SENSITIVE_KEYS, TOKEN_KEYS

        # TOKEN_KEYS should be same reference or equal to SENSITIVE_KEYS
        assert TOKEN_KEYS == SENSITIVE_KEYS


class TestUserPathValidation:
    """Verify path traversal prevention."""

    def test_rejects_symlink_escape(self, tmp_path):
        from app.core.exceptions import FileNotFoundError as AppFileNotFoundError
        from app.services.data_service import _validate_user_path

        base = tmp_path / "data"
        base.mkdir()
        # Create a symlink that escapes the base dir
        escape_target = tmp_path / "secret"
        escape_target.mkdir()
        (base / "evil_link").symlink_to(escape_target)

        with pytest.raises(AppFileNotFoundError):
            _validate_user_path(base, "evil_link")

    def test_rejects_dotdot_traversal(self, tmp_path):
        from app.core.exceptions import FileNotFoundError as AppFileNotFoundError
        from app.services.data_service import _validate_user_path

        base = tmp_path / "data"
        base.mkdir()

        with pytest.raises(AppFileNotFoundError):
            _validate_user_path(base, "../etc")

    def test_allows_normal_user_id(self, tmp_path):
        from app.services.data_service import _validate_user_path

        base = tmp_path / "data"
        base.mkdir()
        user_dir = base / "user123"
        user_dir.mkdir()

        # Should not raise
        result = _validate_user_path(base, "user123")
        assert result == user_dir


class TestCredentialPathValidation:
    """Verify credential file validation."""

    def test_rejects_symlink_credential(self, tmp_path):
        from app.core.firebase_init import _validate_credential_path

        real_file = tmp_path / "real.json"
        real_file.write_text("{}")
        link = tmp_path / "link.json"
        link.symlink_to(real_file)

        with pytest.raises(RuntimeError, match="symlink"):
            _validate_credential_path(link)

    def test_accepts_regular_file(self, tmp_path):
        from app.core.firebase_init import _validate_credential_path

        cred_file = tmp_path / "cred.json"
        cred_file.write_text("{}")
        # Should not raise
        _validate_credential_path(cred_file)


class TestCredentialAgeCheck:
    """Verify credential age warning."""

    def test_warns_on_old_credential(self, tmp_path, caplog):
        from app.core.firebase_init import _check_credential_age

        cred_file = tmp_path / "old_cred.json"
        cred_file.write_text("{}")
        # Set modification time to 200 days ago
        import time

        old_time = time.time() - (200 * 86400)
        os.utime(cred_file, (old_time, old_time))

        # Add caplog handler directly to the target logger because the
        # "app" logger has propagate=False (set by configure_logging).
        target_logger = logging.getLogger("app.core.firebase_init")
        target_logger.addHandler(caplog.handler)
        caplog.set_level(logging.WARNING)
        try:
            _check_credential_age(cred_file)
        finally:
            target_logger.removeHandler(caplog.handler)

        assert any("older than" in r.message for r in caplog.records)

    def test_no_warning_for_fresh_credential(self, tmp_path, caplog):
        from app.core.firebase_init import _check_credential_age

        cred_file = tmp_path / "fresh_cred.json"
        cred_file.write_text("{}")

        target_logger = logging.getLogger("app.core.firebase_init")
        target_logger.addHandler(caplog.handler)
        caplog.set_level(logging.WARNING)
        try:
            _check_credential_age(cred_file)
        finally:
            target_logger.removeHandler(caplog.handler)

        assert not any("older than" in r.message for r in caplog.records)


class TestAdminEndpointRequiresAuth:
    """Verify admin endpoint is protected."""

    def test_cleanup_metrics_requires_auth(self):
        from app.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/admin/cleanup-metrics")
        # Should require authentication (403 Forbidden from HTTPBearer)
        assert resp.status_code in (401, 403)
