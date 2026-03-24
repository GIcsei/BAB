import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)
_SETTINGS: Optional["Settings"] = None


def _to_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        logger.debug(
            "Boolean environment variable is not set, using default: %s", default
        )
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _to_int(value: Optional[str], default: int) -> int:
    try:
        return int(value) if value is not None else default
    except Exception:
        logger.exception(
            "Failed to convert environment variable to int: %s, using default: %d",
            value,
            default,
        )
        return default


@dataclass(frozen=True)
class Settings:
    raw_app_user_data_dir: Optional[str]
    app_user_data_dir: Path
    netbank_base_dir: Path
    allow_unsafe_deserialize: bool
    app_job_hour: int
    app_job_minute: int
    google_application_credentials: Optional[Path]
    log_level: str
    log_file: str
    log_json: bool
    selenium_downloads_dir: Optional[str]
    local_downloads_dir: Optional[str]
    is_testing: bool  # Based on flag, default test values shall be loaded. After implementation, other test params can be removed and set based on this flag.
    unregister_deletion_days: int
    cors_allowed_origins: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.app_job_hour < 0 or self.app_job_hour > 23:
            raise ValueError("app_job_hour must be between 0 and 23")
        if self.app_job_minute < 0 or self.app_job_minute > 59:
            raise ValueError("app_job_minute must be between 0 and 59")


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is not None:
        logger.debug("Returning cached settings")
        return _SETTINGS

    logger.info("Loading settings from environment variables")

    logger.info("Loading directories...")
    raw_app_user_data_dir = os.getenv("APP_USER_DATA_DIR")
    app_user_data_dir = (
        Path(raw_app_user_data_dir)
        if raw_app_user_data_dir
        else Path("/var/app/user_data")
    )
    selenium_downloads_dir = os.getenv("SELENIUM_DOWNLOADS_DIR")
    local_downloads_dir = os.getenv("LOCAL_DOWNLOADS_DIR")
    netbank_base_dir = (
        Path(raw_app_user_data_dir) / "netbank"
        if raw_app_user_data_dir
        else Path.home() / "netbank"
    )
    logger.info(
        "Directories loaded: app_user_data_dir=%s, selenium_downloads_dir=%s, local_downloads_dir=%s, netbank_base_dir=%s",
        app_user_data_dir,
        selenium_downloads_dir,
        local_downloads_dir,
        netbank_base_dir,
    )

    logger.info("Loading other settings...")
    allow_unsafe_deserialize = _to_bool(
        os.getenv("APP_ALLOW_UNSAFE_DESERIALIZE"), False
    )
    app_job_hour = _to_int(os.getenv("APP_JOB_HOUR"), 18)
    app_job_minute = _to_int(os.getenv("APP_JOB_MINUTE"), 0)
    logger.info(
        "Other settings loaded: allow_unsafe_deserialize=%s, app_job_hour=%d, app_job_minute=%d",
        allow_unsafe_deserialize,
        app_job_hour,
        app_job_minute,
    )

    logger.info("Loading application credentials...")
    google_application_credentials_env = os.getenv("FIRESTORE_CREDENTIALS")
    google_application_credentials = (
        Path(google_application_credentials_env)
        if google_application_credentials_env
        else None
    )

    logger.info("Loading logging settings...")

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("LOG_FILE", "")
    log_json = _to_bool(os.getenv("LOG_JSON"), False)

    logger.info(
        "Logging settings loaded: log_level=%s, log_file=%s, log_json=%s",
        log_level,
        log_file,
        log_json,
    )
    logger.info("Determining testing mode...")

    is_testing = any(
        os.getenv(flag)
        for flag in ("PYTEST_CURRENT_TEST", "PYTEST_RUNNING", "UNIT_TEST")
    )

    logger.info("Testing mode: %s", is_testing)

    unregister_deletion_days = _to_int(os.getenv("APP_UNREGISTER_DELETION_DAYS"), 60)
    logger.info("Unregister deletion days: %d", unregister_deletion_days)

    raw_cors = os.getenv("CORS_ALLOWED_ORIGINS", "")
    cors_allowed_origins: List[str] = (
        [o.strip() for o in raw_cors.split(",") if o.strip()] if raw_cors else ["*"]
    )
    logger.info("CORS allowed origins: %s", cors_allowed_origins)

    if "*" in cors_allowed_origins and not is_testing:
        logger.warning(
            "CORS_ALLOWED_ORIGINS is set to wildcard '*' — restrict in production"
        )

    _SETTINGS = Settings(
        raw_app_user_data_dir=raw_app_user_data_dir,
        app_user_data_dir=app_user_data_dir,
        netbank_base_dir=netbank_base_dir,
        allow_unsafe_deserialize=allow_unsafe_deserialize,
        app_job_hour=app_job_hour,
        app_job_minute=app_job_minute,
        google_application_credentials=google_application_credentials,
        log_level=log_level,
        log_file=log_file,
        log_json=log_json,
        selenium_downloads_dir=selenium_downloads_dir,
        local_downloads_dir=local_downloads_dir,
        is_testing=is_testing,
        unregister_deletion_days=unregister_deletion_days,
        cors_allowed_origins=cors_allowed_origins,
    )
    return _SETTINGS
