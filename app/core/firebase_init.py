import logging
import os
import platform
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union, cast

import firebase_admin
from firebase_admin import credentials

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_firebase_app: Optional[firebase_admin.App] = None
_project_id: Optional[str] = None
_init_lock = threading.Lock()
_TEST_PROJECT_ID = "test-project"


def _validate_credential_path(path: Path) -> None:
    """Reject symlinks and warn about insecure locations / permissions."""
    if path.is_symlink():
        raise RuntimeError(
            f"Credential path '{path}' is a symlink — refusing to load for security reasons"
        )

    # Warn if the credential file sits inside the source tree
    # __file__ is app/core/firebase_init.py → .parent.parent.parent = project root
    project_root = Path(__file__).resolve().parent.parent.parent
    try:
        path.resolve().relative_to(project_root)
        logger.warning(
            "Credential file %s is inside the project/source directory — "
            "consider storing credentials outside the source tree",
            path,
        )
    except ValueError:
        pass  # Not inside project dir – good

    # Warn about world-readable permissions (Unix only)
    if platform.system() != "Windows":
        try:
            mode = path.stat().st_mode
            if mode & 0o044:
                logger.warning(
                    "Credential file %s has overly permissive permissions (%o) — "
                    "consider restricting to owner-only (chmod 600)",
                    path,
                    mode & 0o777,
                )
        except OSError:
            pass


def _check_credential_age(path: Path) -> None:
    """Log a warning when the credential file is older than the configured threshold."""
    max_age_days = int(os.getenv("CREDENTIAL_MAX_AGE_DAYS", "90"))
    try:
        mtime = path.stat().st_mtime
        age_days = (time.time() - mtime) / 86400
        if age_days > max_age_days:
            logger.warning(
                "Service-account key file %s is older than %d days (%.0f days) — "
                "consider rotating the key",
                path,
                max_age_days,
                age_days,
            )
    except OSError:
        logger.debug("Could not stat file %s for age check", path)


def is_testing_env() -> bool:
    return bool(
        os.getenv("PYTEST_CURRENT_TEST")
        or os.getenv("PYTEST_RUNNING")
        or os.getenv("UNIT_TEST")
    )


def initialize_firebase_admin(force: bool = False) -> Optional[firebase_admin.App]:
    global _firebase_app, _project_id
    if _firebase_app and not force:
        logger.debug("Firebase admin already initialized, returning existing app")
        return _firebase_app

    if is_testing_env():
        if not _project_id:
            _project_id = os.getenv("FIREBASE_TEST_PROJECT_ID", _TEST_PROJECT_ID)
        logger.info(
            "Skipping firebase-admin initialization in test mode; using project_id=%s",
            _project_id,
        )
        return None

    with _init_lock:
        if firebase_admin._apps:
            _firebase_app = firebase_admin.get_app()
            if not _project_id:
                try:
                    cred = _firebase_app.credential
                    _project_id = getattr(cred, "project_id", None)
                except Exception:
                    _project_id = None
            logger.debug("Reusing existing firebase-admin app")
            return _firebase_app

        cred = cast(credentials.Certificate, get_credential())
        _firebase_app = firebase_admin.initialize_app(cred)
        _project_id = cred.project_id
        logger.info("firebase-admin initialized with project_id=%s", _project_id)
        return _firebase_app


def get_project_id(allow_default: bool = False) -> str:
    global _project_id
    if _project_id:
        return _project_id

    if allow_default:
        fallback = os.environ.get("FIREBASE_PROJECT_ID", _TEST_PROJECT_ID)
        _project_id = fallback
        return _project_id

    initialize_firebase_admin()
    if _project_id:
        return _project_id
    raise RuntimeError("Firebase not initialized; project_id unavailable")


def get_credential(
    as_dict: bool = False,
) -> Union[credentials.Certificate, Dict[str, Any], None]:
    if is_testing_env():
        logger.info("Skipping credential loading in test mode")
        return None
    settings = get_settings()
    cred_path = settings.google_application_credentials
    if not cred_path:
        fallback = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        cred_path = Path(fallback) if fallback else None
    if not cred_path or not Path(cred_path).is_file():
        raise RuntimeError(
            "GOOGLE_APPLICATION_CREDENTIALS must point to a readable service account JSON file"
        )
    _validate_credential_path(Path(cred_path))
    _check_credential_age(Path(cred_path))
    if not as_dict:
        return credentials.Certificate(str(cred_path))

    import json

    with open(cred_path, encoding="utf-8") as json_file:
        json_data = json.load(json_file)
        logger.debug("Credential JSON loaded successfully from %s", cred_path)
        return cast(Dict[str, Any], json_data)
