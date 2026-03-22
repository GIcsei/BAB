"""Enables narrow exception handling and consistent error mapping to HTTP responses."""

from typing import Optional


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


# ===== Authentication & Authorization =====
class AuthException(AppException):
    """Base for auth-related errors."""

    def __init__(self, message: str, code: str = "AUTH_ERROR", status_code: int = 401):
        super().__init__(message, code, status_code)


class InvalidTokenError(AuthException):
    """Token is invalid, expired, or malformed."""

    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message, "INVALID_TOKEN", 401)


class TokenExpiredError(AuthException):
    """Token has expired."""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(message, "TOKEN_EXPIRED", 401)


class MissingTokenError(AuthException):
    """Authorization header missing or malformed."""

    def __init__(self, message: str = "Missing or invalid Authorization header"):
        super().__init__(message, "MISSING_TOKEN", 401)


class LoginFailedError(AuthException):
    """Login failed due to invalid credentials or service error."""

    def __init__(self, message: str = "Login failed"):
        super().__init__(message, "LOGIN_FAILED", 401)


class RegistrationFailedError(AuthException):
    """Registration failed due to invalid data or service error."""

    def __init__(self, message: str = "Registration failed"):
        super().__init__(message, "REGISTRATION_FAILED", 400)


class UserBlockedError(AuthException):
    """User account is blocked (pending deletion)."""

    def __init__(self, message: str = "User account is blocked"):
        super().__init__(message, "USER_BLOCKED", 403)


# ===== Storage & Data Access =====
class StorageException(AppException):
    """Base for storage-related errors."""

    def __init__(
        self, message: str, code: str = "STORAGE_ERROR", status_code: int = 500
    ):
        super().__init__(message, code, status_code)


class FileNotFoundError(StorageException):
    """File does not exist or is not accessible."""

    def __init__(self, filename: str = ""):
        msg = f"File not found: {filename}" if filename else "File not found"
        super().__init__(msg, "FILE_NOT_FOUND", 404)


class FileSizeExceededError(StorageException):
    """File size exceeds allowed limit."""

    def __init__(self, size_mb: int = 0, max_mb: int = 500):
        msg = f"File size {size_mb}MB exceeds maximum {max_mb}MB"
        super().__init__(msg, "FILE_SIZE_EXCEEDED", 413)


class DeserializationError(StorageException):
    """Failed to deserialize file contents."""

    def __init__(self, filename: str = "", reason: str = ""):
        msg = (
            f"Failed to deserialize {filename}: {reason}"
            if filename
            else f"Deserialization failed: {reason}"
        )
        super().__init__(msg, "DESERIALIZATION_ERROR", 400)


class DeserializationDisabledError(StorageException):
    """Unsafe deserialization is disabled."""

    def __init__(self, message: str = "Unsafe deserialization is disabled"):
        super().__init__(message, "DESERIALIZATION_DISABLED", 403)


# ===== Scheduler & Background Jobs =====
class SchedulerException(AppException):
    """Base for scheduler-related errors."""

    def __init__(
        self, message: str, code: str = "SCHEDULER_ERROR", status_code: int = 500
    ):
        super().__init__(message, code, status_code)


class JobNotFoundError(SchedulerException):
    """Scheduled job not found for user."""

    def __init__(self, user_id: str = ""):
        msg = (
            f"No scheduled job for user {user_id}"
            if user_id
            else "No scheduled job found"
        )
        super().__init__(msg, "JOB_NOT_FOUND", 404)


class JobStartError(SchedulerException):
    """Failed to start a scheduled job."""

    def __init__(self, user_id: str = ""):
        msg = (
            f"Failed to start job for user {user_id}"
            if user_id
            else "Failed to start job"
        )
        super().__init__(msg, "JOB_START_ERROR", 500)


# ===== External Services (Firebase, etc.) =====
class ExternalServiceException(AppException):
    """Base for external service errors (Firebase, Identity Toolkit, etc.)."""

    def __init__(
        self, message: str, code: str = "EXTERNAL_ERROR", status_code: int = 502
    ):
        super().__init__(message, code, status_code)


class FirebaseError(ExternalServiceException):
    """Firebase/Firestore operation failed."""

    def __init__(self, message: str = "Firebase operation failed"):
        super().__init__(message, "FIREBASE_ERROR", 502)


class IdentityToolkitError(ExternalServiceException):
    """Identity Toolkit API error."""

    def __init__(self, message: str = "Identity verification failed"):
        super().__init__(message, "IDENTITY_TOOLKIT_ERROR", 502)


# ===== Startup & Configuration =====
class StartupException(AppException):
    """Base for startup errors."""

    def __init__(
        self, message: str, code: str = "STARTUP_ERROR", status_code: int = 500
    ):
        super().__init__(message, code, status_code)


class ConfigurationError(StartupException):
    """Missing or invalid configuration."""

    def __init__(self, missing_vars: Optional[list[str]] = None):
        vars_str = ", ".join(missing_vars) if missing_vars else "unknown"
        msg = f"Missing required environment variables: {vars_str}"
        super().__init__(msg, "CONFIG_ERROR", 500)


class StartupTimeoutError(StartupException):
    """Startup took too long or component failed to become ready."""

    def __init__(self, component: str = ""):
        msg = f"Startup timeout: {component}" if component else "Startup timeout"
        super().__init__(msg, "STARTUP_TIMEOUT", 500)
