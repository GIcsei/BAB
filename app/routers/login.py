from fastapi import APIRouter, HTTPException
from app.schemas.login import LoginRequest, LoginResponse, UserInfo
from app.services.login_service import login_user, logout_user, firebase
from app.services.scheduler import scheduler
import logging

router = APIRouter(prefix="/user", tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.post("/login", response_model=LoginResponse, summary="Create unique user token after successful login")
def login(data: LoginRequest):
    try:
        return login_user(data)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.put("/collect_automatically", response_model=bool, summary="Trigger an immediate run for the current user without affecting the daily schedule")
def trigger_run(data: UserInfo):
    """
    Trigger an immediate job run for the identified user. The existing scheduled job (if any)
    is not modified; this runs the job once in a background thread.

    Identification:
    - Prefer `access_token` (idToken) returned at login.
    - Fallback to `user_name` which is matched against stored token emails.
    """
    user_id = None
    if data.access_token:
        user_id = firebase.get_user_id_by_token(data.access_token)

    if not user_id and data.user_name:
        for uid, tok in firebase.user_tokens.items():
            if tok.get("email") == data.user_name:
                user_id = uid
                break

    if not user_id:
        logger.warning("trigger_run: user not found (access_token=%s user_name=%s)", data.access_token, data.user_name)
        raise HTTPException(status_code=404, detail="User not found")

    ok = scheduler.trigger_run_for_user(user_id)
    if not ok:
        logger.error("Failed to trigger immediate run for user %s", user_id)
        raise HTTPException(status_code=500, detail="Failed to trigger job")
    return True


@router.post("/logout", response_model=bool, summary="Logout user, stop their scheduled job and remove stored credentials")
def logout(data: UserInfo):
    try:
        return logout_user(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/next_run", summary="Get seconds until next scheduled run for the current user")
def next_run(data: UserInfo):
    """
    Returns JSON with next run info for the user identified by access_token (preferred) or by user_name/email.
    Response: { "seconds_until_next_run": float, "next_run_timestamp_ms": int }
    """
    user_id = None
    if data.access_token:
        user_id = firebase.get_user_id_by_token(data.access_token)

    if not user_id and data.user_name:
        for uid, tok in firebase.user_tokens.items():
            if tok.get("email") == data.user_name:
                user_id = uid
                break

    if not user_id:
        logger.warning("next_run: user not found (access_token=%s user_name=%s)", data.access_token, data.user_name)
        raise HTTPException(status_code=404, detail="User not found")

    info = scheduler.get_next_run_for_user(user_id)
    if not info:
        logger.info("next_run: no scheduled job for user %s", user_id)
        raise HTTPException(status_code=404, detail="No scheduled job for user")

    return info