"""Tests for app.core.exceptions – all exception subclasses."""

from app.core.exceptions import (
    AppException,
    AuthException,
    ConfigurationError,
    DeserializationError,
    ExternalServiceException,
    FileSizeExceededError,
    FirebaseError,
    IdentityToolkitError,
    InvalidTokenError,
    JobNotFoundError,
    JobStartError,
    LoginFailedError,
    MissingTokenError,
    SchedulerException,
    StartupException,
    StartupTimeoutError,
    StorageException,
    TokenExpiredError,
)
from app.core.exceptions import FileNotFoundError as AppFileNotFoundError

# ── AppException base ──────────────────────────────────────────────────────


def test_app_exception_defaults():
    exc = AppException("oops")
    assert exc.message == "oops"
    assert exc.code == "INTERNAL_ERROR"
    assert exc.status_code == 500
    assert str(exc) == "oops"


def test_app_exception_custom():
    exc = AppException("custom msg", code="MY_CODE", status_code=418)
    assert exc.code == "MY_CODE"
    assert exc.status_code == 418


# ── Auth exceptions ────────────────────────────────────────────────────────


def test_auth_exception_defaults():
    exc = AuthException("auth error")
    assert exc.status_code == 401
    assert exc.code == "AUTH_ERROR"


def test_invalid_token_error():
    exc = InvalidTokenError()
    assert exc.code == "INVALID_TOKEN"
    assert exc.status_code == 401
    assert "Invalid" in exc.message


def test_invalid_token_error_custom_message():
    exc = InvalidTokenError("my msg")
    assert exc.message == "my msg"


def test_token_expired_error():
    exc = TokenExpiredError()
    assert exc.code == "TOKEN_EXPIRED"
    assert exc.status_code == 401


def test_missing_token_error():
    exc = MissingTokenError()
    assert exc.code == "MISSING_TOKEN"
    assert exc.status_code == 401


def test_login_failed_error():
    exc = LoginFailedError()
    assert exc.code == "LOGIN_FAILED"
    assert exc.status_code == 401
    assert "Login" in exc.message


def test_login_failed_error_custom():
    exc = LoginFailedError("bad creds")
    assert exc.message == "bad creds"


# ── Storage exceptions ─────────────────────────────────────────────────────


def test_storage_exception_defaults():
    exc = StorageException("storage error")
    assert exc.status_code == 500
    assert exc.code == "STORAGE_ERROR"


def test_file_not_found_error_with_name():
    exc = AppFileNotFoundError("report.pkl")
    assert exc.code == "FILE_NOT_FOUND"
    assert exc.status_code == 404
    assert "report.pkl" in exc.message


def test_file_not_found_error_no_name():
    exc = AppFileNotFoundError()
    assert "File not found" in exc.message


def test_file_size_exceeded_error():
    exc = FileSizeExceededError(600, 500)
    assert exc.code == "FILE_SIZE_EXCEEDED"
    assert exc.status_code == 413
    assert "600" in exc.message
    assert "500" in exc.message


def test_file_size_exceeded_error_defaults():
    exc = FileSizeExceededError()
    assert exc.status_code == 413


def test_deserialization_error_with_details():
    exc = DeserializationError("file.pkl", "bad magic")
    assert exc.code == "DESERIALIZATION_ERROR"
    assert exc.status_code == 400
    assert "file.pkl" in exc.message
    assert "bad magic" in exc.message


def test_deserialization_error_no_filename():
    exc = DeserializationError(reason="oops")
    assert "oops" in exc.message


# ── Scheduler exceptions ───────────────────────────────────────────────────


def test_scheduler_exception_defaults():
    exc = SchedulerException("sched error")
    assert exc.status_code == 500
    assert exc.code == "SCHEDULER_ERROR"


def test_job_not_found_error_with_user():
    exc = JobNotFoundError("alice")
    assert exc.code == "JOB_NOT_FOUND"
    assert exc.status_code == 404
    assert "alice" in exc.message


def test_job_not_found_error_no_user():
    exc = JobNotFoundError()
    assert "No scheduled job" in exc.message


def test_job_start_error_with_user():
    exc = JobStartError("bob")
    assert exc.code == "JOB_START_ERROR"
    assert exc.status_code == 500
    assert "bob" in exc.message


def test_job_start_error_no_user():
    exc = JobStartError()
    assert "Failed to start job" in exc.message


# ── External service exceptions ────────────────────────────────────────────


def test_external_service_exception_defaults():
    exc = ExternalServiceException("ext error")
    assert exc.status_code == 502
    assert exc.code == "EXTERNAL_ERROR"


def test_firebase_error():
    exc = FirebaseError()
    assert exc.code == "FIREBASE_ERROR"
    assert exc.status_code == 502


def test_firebase_error_custom():
    exc = FirebaseError("db down")
    assert exc.message == "db down"


def test_identity_toolkit_error():
    exc = IdentityToolkitError()
    assert exc.code == "IDENTITY_TOOLKIT_ERROR"
    assert exc.status_code == 502


# ── Startup exceptions ─────────────────────────────────────────────────────


def test_startup_exception_defaults():
    exc = StartupException("startup error")
    assert exc.status_code == 500
    assert exc.code == "STARTUP_ERROR"


def test_configuration_error_with_vars():
    exc = ConfigurationError(["VAR_A", "VAR_B"])
    assert exc.code == "CONFIG_ERROR"
    assert exc.status_code == 500
    assert "VAR_A" in exc.message
    assert "VAR_B" in exc.message


def test_configuration_error_no_vars():
    exc = ConfigurationError()
    assert "unknown" in exc.message


def test_startup_timeout_error_with_component():
    exc = StartupTimeoutError("firebase")
    assert exc.code == "STARTUP_TIMEOUT"
    assert exc.status_code == 500
    assert "firebase" in exc.message


def test_startup_timeout_error_no_component():
    exc = StartupTimeoutError()
    assert "Startup timeout" in exc.message


# ── Inheritance checks ─────────────────────────────────────────────────────


def test_auth_exceptions_are_app_exceptions():
    for cls in [
        InvalidTokenError,
        TokenExpiredError,
        MissingTokenError,
        LoginFailedError,
    ]:
        assert isinstance(cls(), AppException)


def test_storage_exceptions_are_app_exceptions():
    for cls in [
        AppFileNotFoundError,
        FileSizeExceededError,
    ]:
        assert isinstance(cls(), AppException)


def test_scheduler_exceptions_are_app_exceptions():
    for cls in [JobNotFoundError, JobStartError]:
        assert isinstance(cls(), AppException)


def test_external_exceptions_are_app_exceptions():
    for cls in [FirebaseError, IdentityToolkitError]:
        assert isinstance(cls(), AppException)


def test_startup_exceptions_are_app_exceptions():
    for cls in [ConfigurationError, StartupTimeoutError]:
        assert isinstance(cls(), AppException)
