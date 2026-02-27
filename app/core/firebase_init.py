import logging
import os
import threading
from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger(__name__)

_firebase_app: Optional[firebase_admin.App] = None
_project_id: Optional[str] = None
_init_lock = threading.Lock()
_TEST_PROJECT_ID = "test-project"


def is_testing_env() -> bool:
    return bool(
        os.getenv("PYTEST_CURRENT_TEST")
        or os.getenv("PYTEST_RUNNING")
        or os.getenv("UNIT_TEST")
    )


def initialize_firebase_admin(force: bool = False) -> Optional[firebase_admin.App]:
    global _firebase_app, _project_id
    if _firebase_app and not force:
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
        if _firebase_app and not force:
            return _firebase_app

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

        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not cred_path or not Path(cred_path).is_file():
            raise RuntimeError(
                "GOOGLE_APPLICATION_CREDENTIALS must point to a readable service account JSON file"
            )

        cred = credentials.Certificate(cred_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        _project_id = cred.project_id or os.getenv("FIREBASE_PROJECT_ID")
        logger.info("firebase-admin initialized with project_id=%s", _project_id)
        return _firebase_app


def get_project_id(allow_default: bool = False) -> str:
    global _project_id
    if _project_id:
        return _project_id

    if allow_default:
        fallback = (
            os.getenv("FIREBASE_PROJECT_ID")
            or os.getenv("FIREBASE_TEST_PROJECT_ID")
            or _TEST_PROJECT_ID
        )
        _project_id = fallback
        return _project_id

    initialize_firebase_admin()
    if _project_id:
        return _project_id
    raise RuntimeError("Firebase not initialized; project_id unavailable")
