import json
import logging
import os
from typing import Any, Dict, Optional

from app.core.config import Settings, get_settings
from app.core.firestore_handler.QueryHandler import Firebase
from app.infrastructure.sched.scheduler import Scheduler
from app.schemas.login import LoginRequest, LoginResponse

logger = logging.getLogger(__name__)


def _get_settings() -> Settings:
    return get_settings()


def _extract_user_id(user_obj: Dict[str, Any]) -> Optional[str]:
    return (
        user_obj.get("userId")
        or user_obj.get("localId")
        or user_obj.get("user_id")
        or user_obj.get("uid")
    )


def login_user(
    data: LoginRequest, scheduler: Scheduler, firebase: Firebase
) -> LoginResponse:
    logger.info("Login attempt for email=%s", data.email)

    settings = _get_settings()
    base_data_dir = settings.app_user_data_dir
    base_data_dir.mkdir(parents=True, exist_ok=True)

    temp_token_path = base_data_dir / "auth_token_tmp.json"
    auth_client, _ = firebase.auth(temp_token_path)

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
        refresh_token = user.get("refreshToken")
        if not isinstance(refresh_token, str):
            raise ValueError("No refreshToken returned from authentication provider.")
        token_copy: Dict[str, str] = {
            "idToken": id_token,
            "refreshToken": refresh_token,
            "userId": user_id,
            "email": data.email,
        }
        with open(cred_path, "w", encoding="utf-8") as file:
            json.dump(token_copy, file)
        try:
            os.chmod(str(cred_path), 0o600)
        except Exception:
            logger.debug(
                "chmod on credentials file may not be supported in this environment"
            )

        firebase.register_user_tokens(user_id, token_copy, cred_path)
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
    except Exception as exc:
        logger.exception("Login failed for email=%s: %s", data.email, exc)
        raise ValueError(f"Login failed: {exc}")


def logout_user(user_id: str, scheduler: Scheduler, firebase: Firebase) -> bool:
    settings = _get_settings()
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

    firebase.clear_user(user_id)
    logger.info("Cleared in-memory token registry for user %s", user_id)

    return True
