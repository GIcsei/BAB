import logging

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user_id
from app.core.error_mapping import exception_to_http
from app.core.exceptions import JobNotFoundError, JobStartError, LoginFailedError
from app.schemas.login import LoginRequest, LoginResponse
from app.services.login_service import login_user, logout_user
from app.services.scheduler import scheduler

router = APIRouter(prefix="/user", tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Create unique user token after successful login",
)
def login(data: LoginRequest):
    try:
        return login_user(data)
    except LoginFailedError as exc:
        logger.warning("Login failed for email: %s", data.email)
        raise exception_to_http(exc)
    except Exception as exc:
        logger.exception("Unexpected error during login for email: %s", data.email)
        raise exception_to_http(LoginFailedError(str(exc)))


@router.put(
    "/collect_automatically",
    response_model=bool,
    summary="Trigger an immediate run for the current user without affecting the daily schedule",
)
def trigger_run(current_user_id: str = Depends(get_current_user_id)):
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
def logout(current_user_id: str = Depends(get_current_user_id)):
    try:
        return logout_user(current_user_id)
    except Exception as exc:
        logger.exception("Logout failed for user: %s", current_user_id)
        raise exception_to_http(exc)


@router.post(
    "/next_run", summary="Get seconds until next scheduled run for the current user"
)
def next_run(current_user_id: str = Depends(get_current_user_id)):
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
