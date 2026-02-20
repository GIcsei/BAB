import logging

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_current_user_id
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
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.put(
    "/collect_automatically",
    response_model=bool,
    summary="Trigger an immediate run for the current user without affecting the daily schedule",
)
def trigger_run(current_user_id: str = Depends(get_current_user_id)):
    ok = scheduler.trigger_run_for_user(current_user_id)
    if not ok:
        logger.error("Failed to trigger immediate run for user %s", current_user_id)
        raise HTTPException(status_code=500, detail="Failed to trigger job")
    return True


@router.post(
    "/logout",
    response_model=bool,
    summary="Logout user, stop their scheduled job and remove stored credentials",
)
def logout(current_user_id: str = Depends(get_current_user_id)):
    try:
        return logout_user(current_user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/next_run", summary="Get seconds until next scheduled run for the current user"
)
def next_run(current_user_id: str = Depends(get_current_user_id)):
    info = scheduler.get_next_run_for_user(current_user_id)
    if not info:
        logger.info("next_run: no scheduled job for user %s", current_user_id)
        raise HTTPException(status_code=404, detail="No scheduled job for user")

    return info
