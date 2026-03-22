import logging
from typing import Any, Dict, cast

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.auth import get_current_user, get_current_user_id, get_firebase_dep
from app.core.error_mapping import exception_to_http
from app.core.exceptions import (
    JobNotFoundError,
    JobStartError,
    LoginFailedError,
    RegistrationFailedError,
)
from app.core.firestore_handler.QueryHandler import Firebase
from app.infrastructure.sched.scheduler import Scheduler
from app.schemas.login import (
    JobStatusResponse,
    LoginRequest,
    LoginResponse,
    NextRunInfo,
    PasswordResetRequest,
    PasswordResetResponse,
    RegisterRequest,
    RegisterResponse,
    UnregisterResponse,
    UserMeResponse,
)
from app.services.login_service import (
    login_user,
    logout_user,
    register_user,
    request_password_reset,
    unregister_user,
)

router = APIRouter(prefix="/user", tags=["Authentication"])
logger = logging.getLogger(__name__)


def get_scheduler_dep(request: Request) -> Scheduler:
    scheduler = cast(Scheduler, getattr(request.app.state, "scheduler", None))
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler unavailable")
    return scheduler


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=201,
    summary="Register a new user with email and password",
)
def register(
    data: RegisterRequest,
    scheduler: Scheduler = Depends(get_scheduler_dep),
    firebase: Firebase = Depends(get_firebase_dep),
) -> RegisterResponse:
    try:
        return register_user(data, scheduler, firebase)
    except RegistrationFailedError as exc:
        logger.warning("Registration failed for email: %s", data.email)
        raise exception_to_http(exc)
    except Exception as exc:
        logger.exception(
            "Unexpected error during registration for email: %s", data.email
        )
        raise exception_to_http(RegistrationFailedError(str(exc)))


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Create unique user token after successful login",
)
def login(
    data: LoginRequest,
    scheduler: Scheduler = Depends(get_scheduler_dep),
    firebase: Firebase = Depends(get_firebase_dep),
) -> LoginResponse:
    try:
        return login_user(data, scheduler, firebase)
    except LoginFailedError as exc:
        logger.warning("Login failed for email: %s", data.email)
        raise exception_to_http(exc)
    except Exception as exc:
        logger.exception("Unexpected error during login for email: %s", data.email)
        raise exception_to_http(LoginFailedError(str(exc)))


@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="Return the authenticated user's identity",
)
def me(current_user: Dict[str, Any] = Depends(get_current_user)) -> UserMeResponse:
    return UserMeResponse(user_id=current_user["user_id"], email=current_user.get("email"))


@router.get(
    "/job-status",
    response_model=JobStatusResponse,
    summary="Get job status for the authenticated user",
)
def job_status(
    current_user_id: str = Depends(get_current_user_id),
    scheduler: Scheduler = Depends(get_scheduler_dep),
) -> JobStatusResponse:
    try:
        info = scheduler.get_next_run_for_user(current_user_id)
        has_job = info is not None
        next_run = NextRunInfo(**info) if info else None

        # Check deletion pending
        from app.core.config import get_settings
        from app.services.user_deletion_service import get_pending_deletion

        settings = get_settings()
        user_dir = settings.app_user_data_dir / current_user_id
        pending = get_pending_deletion(user_dir)
        deletion_pending = pending is not None

        return JobStatusResponse(
            user_id=current_user_id,
            has_scheduled_job=has_job,
            next_run=next_run,
            deletion_pending=deletion_pending,
        )
    except Exception as exc:
        logger.exception("Error getting job status for user: %s", current_user_id)
        raise exception_to_http(exc)


@router.put(
    "/collect_automatically",
    response_model=bool,
    summary="Trigger an immediate run for the current user without affecting the daily schedule",
)
def trigger_run(
    current_user_id: str = Depends(get_current_user_id),
    scheduler: Scheduler = Depends(get_scheduler_dep),
) -> bool:
    try:
        ok = scheduler.trigger_run_for_user(current_user_id)
        if not ok:
            raise JobStartError(current_user_id)
        return True
    except JobStartError as exc:
        logger.error("Failed to trigger job for user: %s", current_user_id)
        raise exception_to_http(exc)
    except Exception as exc:
        logger.exception(
            "Unexpected error triggering job for user: %s", current_user_id
        )
        logger.exception(exc)
        raise exception_to_http(JobStartError(current_user_id))


@router.post(
    "/logout",
    response_model=bool,
    summary="Logout user, stop their scheduled job and remove stored credentials",
)
def logout(
    current_user_id: str = Depends(get_current_user_id),
    scheduler: Scheduler = Depends(get_scheduler_dep),
    firebase: Firebase = Depends(get_firebase_dep),
) -> bool:
    try:
        return logout_user(current_user_id, scheduler, firebase)
    except Exception as exc:
        logger.exception("Logout failed for user: %s", current_user_id)
        raise exception_to_http(exc)


@router.post(
    "/unregister",
    response_model=UnregisterResponse,
    summary="Unregister user: stop jobs and schedule account deletion in 60 days",
)
def unregister(
    current_user_id: str = Depends(get_current_user_id),
    scheduler: Scheduler = Depends(get_scheduler_dep),
    firebase: Firebase = Depends(get_firebase_dep),
) -> UnregisterResponse:
    try:
        return unregister_user(current_user_id, scheduler, firebase)
    except Exception as exc:
        logger.exception("Unregister failed for user: %s", current_user_id)
        raise exception_to_http(exc)


@router.post(
    "/next_run",
    response_model=NextRunInfo,
    summary="Get seconds until next scheduled run for the current user",
)
def next_run(
    current_user_id: str = Depends(get_current_user_id),
    scheduler: Scheduler = Depends(get_scheduler_dep),
) -> Dict[str, Any]:
    try:
        info = scheduler.get_next_run_for_user(current_user_id)
        if not info:
            raise JobNotFoundError(current_user_id)
        return info
    except JobNotFoundError as exc:
        logger.info("No scheduled job for user: %s", current_user_id)
        raise exception_to_http(exc)
    except Exception as exc:
        logger.exception("Error retrieving next run for user: %s", current_user_id)
        raise exception_to_http(exc)


@router.get(
    "/next_run",
    response_model=NextRunInfo,
    summary="Get seconds until next scheduled run for the current user",
)
def next_run_get(
    current_user_id: str = Depends(get_current_user_id),
    scheduler: Scheduler = Depends(get_scheduler_dep),
) -> Dict[str, Any]:
    try:
        info = scheduler.get_next_run_for_user(current_user_id)
        if not info:
            raise JobNotFoundError(current_user_id)
        return info
    except JobNotFoundError as exc:
        logger.info("No scheduled job for user: %s", current_user_id)
        raise exception_to_http(exc)
    except Exception as exc:
        logger.exception("Error retrieving next run for user: %s", current_user_id)
        raise exception_to_http(exc)


@router.post(
    "/password-reset",
    response_model=PasswordResetResponse,
    summary="Request a password reset email",
)
def password_reset(
    data: PasswordResetRequest,
    firebase: Firebase = Depends(get_firebase_dep),
) -> PasswordResetResponse:
    try:
        result = request_password_reset(data.email, firebase)
        return PasswordResetResponse(**result)
    except Exception:
        logger.exception("Password reset request failed for email: %s", data.email)
        # Always return success to prevent email enumeration
        return PasswordResetResponse(
            message="If the email is registered, a password reset link has been sent."
        )
