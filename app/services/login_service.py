import json
import logging
import os
import threading
from typing import Optional

from app.core.config import get_settings
from app.core.firebase_init import get_project_id, initialize_firebase_admin
from app.core.firestore_handler.QueryHandler import Firebase, initialize_app
from app.infrastructure.sched.scheduler import Scheduler
from app.schemas.login import LoginRequest, LoginResponse

logger = logging.getLogger(__name__)

settings = get_settings()

_firebase_lock = threading.Lock()
_firebase_instance: Optional[Firebase] = None


class _FirebaseAccessor:
    def __getattr__(self, name):
        return getattr(get_firebase(), name)


firebase = _FirebaseAccessor()


def get_firebase() -> Firebase:
    global _firebase_instance
    with _firebase_lock:
        if _firebase_instance is None:
            initialize_firebase_admin()
            config = {
                "projectId": get_project_id(allow_default=True),
            }
            _firebase_instance = initialize_app(config)
    return _firebase_instance


def _extract_user_id(user_obj: dict) -> Optional[str]:
    return (
        user_obj.get("userId")
        or user_obj.get("localId")
        or user_obj.get("user_id")
        or user_obj.get("uid")
    )


def login_user(data: LoginRequest, scheduler: Scheduler) -> LoginResponse:
    logger.info("Login attempt for email=%s", data.email)

    base_data_dir = settings.app_user_data_dir
    base_data_dir.mkdir(parents=True, exist_ok=True)

    temp_token_path = base_data_dir / "auth_token_tmp.json"
    auth_client, _ = get_firebase().auth(temp_token_path)

    try:
        user = auth_client.sign_in_with_email_and_password(data.email, data.password)
        logger.debug("Auth response keys: %s", list(user.keys()))

        id_token = user.get("idToken")
        if not id_token:
            logger.error(
                "Authentication did not return idToken for email=%s", data.email
            )
            raise ValueError("No idToken returned from authentication provider.")

        user_id = _extract_user_id(user)
        if not user_id:
            safe_email = data.email.replace("@", "_at_").replace(".", "_dot_")
            user_id = f"user_{safe_email}"
            logger.debug("Falling back to safe email as user_id: %s", user_id)

        user_dir = base_data_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(str(user_dir), 0o700)
        except Exception:
            logger.debug("chmod on user_dir may not be supported in this environment")

        cred_path = user_dir / "credentials.json"
        token_copy = {
            "idToken": user.get("idToken"),
            "refreshToken": user.get("refreshToken"),
            "userId": user.get("localId") or user.get("user_id") or user.get("userId"),
            "email": data.email,
        }
        with open(cred_path, "w", encoding="utf-8") as f:
            json.dump(token_copy, f)
        try:
            os.chmod(str(cred_path), 0o600)
        except Exception:
            logger.debug(
                "chmod on credentials file may not be supported in this environment"
            )

        get_firebase().register_user_tokens(user_id, token_copy, cred_path)
        logger.info("User %s logged in and token registered", user_id)

        target_hour = settings.app_job_hour
        target_minute = settings.app_job_minute
        scheduler.start_job_for_user(user_id, user_dir, target_hour, target_minute)
        logger.info(
            "Scheduled daily job for user %s at %02d:%02d",
            user_id,
            target_hour,
            target_minute,
        )

        return LoginResponse(access_token=id_token, message="Login successful")
    except Exception as e:
        logger.exception("Login failed for email=%s: %s", data.email, e)
        raise ValueError(f"Login failed: {e}")


def logout_user(user_id: str, scheduler: Scheduler) -> bool:
    base_data_dir = settings.app_user_data_dir

    if not user_id:
        logger.warning("Logout attempt for unknown user")
        raise ValueError("User not found")

    scheduler.stop_job_for_user(user_id)
    logger.info("Stopped scheduled job for user %s", user_id)

    cred_path = base_data_dir / user_id / "credentials.json"
    try:
        if cred_path.exists():
            cred_path.unlink()
            logger.info("Removed credentials file for user %s", user_id)
    except Exception:
        logger.exception("Failed to remove credentials file for user %s", user_id)

    get_firebase().clear_user(user_id)
    logger.info("Cleared in-memory token registry for user %s", user_id)

    return True
