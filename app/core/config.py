import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_SETTINGS: Optional["Settings"] = None


def _to_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _to_int(value: Optional[str], default: int) -> int:
    try:
        return int(value) if value is not None else default
    except Exception:
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
    firebase_project_id: Optional[str]
    firebase_test_project_id: Optional[str]
    firebase_api_key: Optional[str]
    log_level: str
    log_file: str
    log_json: bool
    selenium_downloads_dir: Optional[str]
    local_downloads_dir: Optional[str]
    netbank_master_key: Optional[str]
    is_testing: bool


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is not None:
        return _SETTINGS

    raw_app_user_data_dir = os.getenv("APP_USER_DATA_DIR")
    app_user_data_dir = (
        Path(raw_app_user_data_dir)
        if raw_app_user_data_dir
        else Path("/var/app/user_data")
    )

    allow_unsafe_deserialize = _to_bool(
        os.getenv("APP_ALLOW_UNSAFE_DESERIALIZE"), False
    )
    app_job_hour = _to_int(os.getenv("APP_JOB_HOUR"), 18)
    app_job_minute = _to_int(os.getenv("APP_JOB_MINUTE"), 0)

    google_application_credentials_env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    google_application_credentials = (
        Path(google_application_credentials_env)
        if google_application_credentials_env
        else None
    )

    firebase_project_id = os.getenv("FIREBASE_PROJECT_ID")
    firebase_test_project_id = os.getenv("FIREBASE_TEST_PROJECT_ID")
    firebase_api_key = os.getenv("FIREBASE_API_KEY")

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("LOG_FILE", "")
    log_json = _to_bool(os.getenv("LOG_JSON"), False)

    selenium_downloads_dir = os.getenv("SELENIUM_DOWNLOADS_DIR")
    local_downloads_dir = os.getenv("LOCAL_DOWNLOADS_DIR")

    netbank_master_key = os.getenv("NETBANK_MASTER_KEY")

    is_testing = any(
        os.getenv(flag)
        for flag in ("PYTEST_CURRENT_TEST", "PYTEST_RUNNING", "UNIT_TEST")
    )

    netbank_base_dir = (
        Path(raw_app_user_data_dir) if raw_app_user_data_dir else Path.home()
    )

    _SETTINGS = Settings(
        raw_app_user_data_dir=raw_app_user_data_dir,
        app_user_data_dir=app_user_data_dir,
        netbank_base_dir=netbank_base_dir,
        allow_unsafe_deserialize=allow_unsafe_deserialize,
        app_job_hour=app_job_hour,
        app_job_minute=app_job_minute,
        google_application_credentials=google_application_credentials,
        firebase_project_id=firebase_project_id,
        firebase_test_project_id=firebase_test_project_id,
        firebase_api_key=firebase_api_key,
        log_level=log_level,
        log_file=log_file,
        log_json=log_json,
        selenium_downloads_dir=selenium_downloads_dir,
        local_downloads_dir=local_downloads_dir,
        netbank_master_key=netbank_master_key,
        is_testing=is_testing,
    )
    return _SETTINGS
