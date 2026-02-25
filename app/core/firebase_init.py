import logging
import os
from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger(__name__)

# singleton firebase-admin app
_firebase_app: Optional[firebase_admin.App] = None
_project_id: Optional[str] = None


def get_project_id() -> str:
    if not _project_id:
        raise RuntimeError("Firebase not initialized; project_id unavailable")
    return _project_id


def initialize_firebase_admin() -> firebase_admin.App:
    """
    Initialize firebase-admin exactly once using GOOGLE_APPLICATION_CREDENTIALS.
    Raises fast if the credential file is missing.
    """
    global _firebase_app, _project_id
    if _firebase_app:
        return _firebase_app

    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path or not Path(cred_path).exists():
        raise RuntimeError(
            "GOOGLE_APPLICATION_CREDENTIALS must point to a readable service account JSON file"
        )

    cred = credentials.Certificate(cred_path)
    _firebase_app = firebase_admin.initialize_app(cred)
    _project_id = cred.project_id
    logger.info("firebase-admin initialized with project_id=%s", _project_id)
    return _firebase_app