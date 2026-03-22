import json
import logging
import os
from typing import Any, Dict, Optional

from app.core.config import Settings, get_settings
from app.core.exceptions import LoginFailedError, RegistrationFailedError
from app.core.firestore_handler.QueryHandler import Firebase
from app.infrastructure.sched.scheduler import Scheduler
from app.schemas.login import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UnregisterResponse,
)
from app.services.user_deletion_service import (
    cancel_user_deletion,
    schedule_user_deletion,
)

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


def _write_credentials(
    user_dir: "os.PathLike[str]",
    user_id: str,
    id_token: str,
    refresh_token: str,
    email: str,
) -> Dict[str, str]:
    """Write credentials.json and return the token dict."""
    cred_path = os.path.join(str(user_dir), "credentials.json")
    token_copy: Dict[str, str] = {
        "idToken": id_token,
        "refreshToken": refresh_token,
        "userId": user_id,
        "email": email,
    }
    with open(cred_path, "w", encoding="utf-8") as fh:
        json.dump(token_copy, fh)
    try:
        os.chmod(cred_path, 0o600)
    except Exception:
        logger.debug(
            "chmod on credentials file may not be supported in this environment"
        )
    return token_copy


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

        # If a deletion was previously scheduled (user re-logged-in within grace
        # period), invalidate it so the account is fully restored.
        if cancel_user_deletion(user_dir):
            logger.info("Pending deletion cancelled for user %s upon re-login", user_id)
            _unblock_user_in_firestore(firebase, user_id)

        refresh_token = user.get("refreshToken")
        if not isinstance(refresh_token, str):
            raise ValueError("No refreshToken returned from authentication provider.")

        token_copy = _write_credentials(
            user_dir, user_id, id_token, refresh_token, data.email
        )

        firebase.register_user_tokens(
            user_id, token_copy, user_dir / "credentials.json"
        )
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
        logger.exception("Login failed for email=%s", data.email)
        raise LoginFailedError("Login failed") from exc


def register_user(
    data: RegisterRequest, scheduler: Scheduler, firebase: Firebase
) -> RegisterResponse:
    """
    Create a new Firebase Auth user, set up the user directory, auto-login,
    and schedule the daily data-collection job.
    """
    logger.info("Registration attempt for email=%s", data.email)

    settings = _get_settings()
    base_data_dir = settings.app_user_data_dir
    base_data_dir.mkdir(parents=True, exist_ok=True)

    temp_token_path = base_data_dir / "auth_token_tmp.json"
    auth_client, _ = firebase.auth(temp_token_path)

    try:
        # Step 1: create the account
        created = auth_client.create_user_with_email_and_password(
            data.email, data.password
        )
        logger.debug("Registration response keys: %s", list(created.keys()))

        id_token = created.get("idToken")
        if not id_token:
            raise ValueError("No idToken returned after registration.")

        user_id = _extract_user_id(created)
        if not user_id:
            safe_email = data.email.replace("@", "_at_").replace(".", "_dot_")
            user_id = f"user_{safe_email}"
            logger.debug("Falling back to safe email as user_id: %s", user_id)

        refresh_token = created.get("refreshToken")
        if not isinstance(refresh_token, str):
            raise ValueError("No refreshToken returned after registration.")

        # Step 2: create user directory
        user_dir = base_data_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(str(user_dir), 0o700)
        except Exception:
            logger.debug("chmod on user_dir may not be supported in this environment")

        # Step 3: persist credentials and register tokens
        token_copy = _write_credentials(
            user_dir, user_id, id_token, refresh_token, data.email
        )
        firebase.register_user_tokens(
            user_id, token_copy, user_dir / "credentials.json"
        )
        logger.info("User %s registered and token stored", user_id)

        # Step 4: schedule daily job (auto-start after registration)
        target_hour = settings.app_job_hour
        target_minute = settings.app_job_minute
        scheduler.start_job_for_user(user_id, user_dir, target_hour, target_minute)
        logger.info(
            "Scheduled daily job for new user %s at %02d:%02d",
            user_id,
            target_hour,
            target_minute,
        )

        return RegisterResponse(
            access_token=id_token,
            user_id=user_id,
            message="Registration successful",
        )
    except Exception as exc:
        logger.exception("Registration failed for email=%s", data.email)
        raise RegistrationFailedError("Registration failed") from exc


def unregister_user(
    user_id: str, scheduler: Scheduler, firebase: Firebase
) -> UnregisterResponse:
    """
    Begin the unregistration process:
    1. Stop all scheduled jobs for the user.
    2. Remove credentials.json so the scheduler won't restart the job.
    3. Schedule deletion 60 days from now (configurable via APP_UNREGISTER_DELETION_DAYS).
    4. Mark the user as blocked in Firestore.
    """
    if not user_id:
        raise ValueError("User not found")

    settings = _get_settings()
    base_data_dir = settings.app_user_data_dir
    deletion_days = settings.unregister_deletion_days

    # Step 1: stop scheduled jobs
    scheduler.stop_job_for_user(user_id)
    logger.info("Stopped scheduled job for user %s", user_id)

    # Step 2: remove credentials.json to prevent job re-scheduling on restart
    cred_path = base_data_dir / user_id / "credentials.json"
    try:
        if cred_path.exists():
            cred_path.unlink()
            logger.info("Removed credentials file for user %s", user_id)
    except Exception:
        logger.exception("Failed to remove credentials file for user %s", user_id)

    # Step 3: schedule deletion
    user_dir = base_data_dir / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    timestamps = schedule_user_deletion(user_dir, user_id, deletion_days)

    # Step 4: clear in-memory token registry and mark blocked in Firestore
    firebase.clear_user(user_id)
    _block_user_in_firestore(firebase, user_id, timestamps["deletion_at_ms"])

    return UnregisterResponse(
        message=(
            f"User unregistered. Account and data will be permanently deleted "
            f"in {deletion_days} days."
        ),
        deletion_scheduled_at_ms=timestamps["requested_at_ms"],
        deletion_at_ms=timestamps["deletion_at_ms"],
    )


def _block_user_in_firestore(
    firebase: Firebase, user_id: str, deletion_at_ms: int
) -> None:
    """Mark the user as blocked in Firestore (best-effort; non-fatal on failure)."""
    try:
        db = firebase.database()
        token = firebase.get_user_token(user_id)
        db.set_document(
            f"users/{user_id}",
            {
                "fields": {
                    "blocked": {"booleanValue": True},
                    "deletion_at_ms": {"integerValue": str(deletion_at_ms)},
                }
            },
            token,
        )
        logger.info("Marked user %s as blocked in Firestore", user_id)
    except Exception:
        logger.exception(
            "Failed to mark user %s as blocked in Firestore (non-fatal)", user_id
        )


def _unblock_user_in_firestore(firebase: Firebase, user_id: str) -> None:
    """Remove the blocked flag from Firestore (best-effort; non-fatal on failure)."""
    try:
        db = firebase.database()
        token = firebase.get_user_token(user_id)
        db.set_document(
            f"users/{user_id}",
            {
                "fields": {
                    "blocked": {"booleanValue": False},
                }
            },
            token,
        )
        logger.info("Unblocked user %s in Firestore", user_id)
    except Exception:
        logger.exception("Failed to unblock user %s in Firestore (non-fatal)", user_id)


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


def request_password_reset(email: str, firebase: Firebase) -> dict:
    """Send a password reset email via Firebase Auth."""
    settings = _get_settings()
    base_data_dir = settings.app_user_data_dir
    base_data_dir.mkdir(parents=True, exist_ok=True)
    temp_token_path = base_data_dir / "auth_token_tmp.json"
    auth_client, _ = firebase.auth(temp_token_path)
    auth_client.send_password_reset_email(email)
    return {"message": "If the email is registered, a password reset link has been sent."}
