import json
import logging
import os
from pathlib import Path
from typing import Optional

from app.core.firestore_handler.QueryHandler import initialize_app
from app.schemas.login import LoginRequest, LoginResponse
from app.services.scheduler import scheduler

logger = logging.getLogger(__name__)

config = {
    "apiKey": "REDACTED_FIREBASE_API_KEY",
    "authDomain": "REDACTED_PROJECT.firebaseapp.com",
    "databaseURL": "https://REDACTED_PROJECT.firebaseio.com/",
    "storageBucket": "REDACTED_PROJECT.firebasestorage.app",
    "projectId": "REDACTED_PROJECT",
}

firebase = initialize_app(config)


def _extract_user_id(user_obj: dict) -> Optional[str]:
    """
    Try to extract a stable user identifier from the auth response.
    The Identity Toolkit returns 'localId' for sign-in responses; refresh responses
    may use different keys. Check common variants.
    """
    return (
        user_obj.get("userId")
        or user_obj.get("localId")
        or user_obj.get("user_id")
        or user_obj.get("uid")
    )


def login_user(data: LoginRequest) -> LoginResponse:
    """
    Sign in user, persist per-user credentials into a secure folder under APP_USER_DATA_DIR,
    and start a per-user daily job that runs at APP_JOB_HOUR:APP_JOB_MINUTE (defaults to 18:00).
    """
    logger.info("Login attempt for email=%s", data.email)

    # Base directory for user data inside the container (configurable)
    base_data_dir = Path(os.getenv("APP_USER_DATA_DIR", "/var/app/user_data"))
    base_data_dir.mkdir(parents=True, exist_ok=True)

    # Obtain auth client using a per-user token path so tokens persist per user
    # We don't yet know user_id; use a temporary path for auth call, will rewrite after sign-in
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

        # create per-user folder and make it accessible only to the container process (0700)
        user_dir = base_data_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(str(user_dir), 0o700)
        except Exception:
            logger.debug("chmod on user_dir may not be supported in this environment")

        # persist credentials for this user only (do not store plaintext password)
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

        # Register token in Firebase singleton via API and set token as active for this session
        # (use the new register_user_tokens API instead of direct user_tokens mutation)
        firebase.register_user_tokens(user_id, token_copy, cred_path)
        firebase.set_active_user(user_id)
        logger.info("User %s logged in and token registered", user_id)

        # schedule job using daily target hour/minute from environment (fallback to 18:00)
        target_hour = int(os.getenv("APP_JOB_HOUR", "18"))
        target_minute = int(os.getenv("APP_JOB_MINUTE", "0"))
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


def logout_user(user_id: str) -> bool:
    """
    Logout user identified by verified user_id.
    Stops user job, removes credentials file, and clears in-memory token.
    """
    base_data_dir = Path(os.getenv("APP_USER_DATA_DIR", "/var/app/user_data"))

    if not user_id:
        logger.warning("Logout attempt for unknown user")
        raise ValueError("User not found")

    # stop scheduled job
    scheduler.stop_job_for_user(user_id)
    logger.info("Stopped scheduled job for user %s", user_id)

    # remove stored credentials file
    cred_path = base_data_dir / user_id / "credentials.json"
    try:
        if cred_path.exists():
            cred_path.unlink()
            logger.info("Removed credentials file for user %s", user_id)
    except Exception:
        logger.exception("Failed to remove credentials file for user %s", user_id)

    # remove from in-memory registry (legacy)
    firebase.clear_user(user_id)
    logger.info("Cleared in-memory token registry for user %s", user_id)

    return True
