import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user_id
from app.core.netbank.credentials import save_user_credentials, delete_user_credentials

router = APIRouter(prefix="/netbank", tags=["netbank"])
logger = logging.getLogger(__name__)


class CredentialsIn(BaseModel):
    username: str
    account_number: str
    password: str


@router.post("/credentials", status_code=201)
def store_credentials(payload: CredentialsIn, current_user_id: str = Depends(get_current_user_id)) -> Any:
    """
    Store NetBroker credentials for the authenticated user.
    Call over HTTPS with authenticated user context and Bearer token returned at login.
    """
    logger.debug("Storing credentials for user_id=%s username=%s account_number=%s", current_user_id, payload.username, payload.account_number)
    try:
        save_user_credentials(
            user_id=current_user_id,
            username=payload.username,
            account_number=payload.account_number,
            password=payload.password,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to save credentials") from exc
    return {"status": "ok"}


@router.delete("/credentials", status_code=204)
def remove_credentials(current_user_id: str = Depends(get_current_user_id)) -> None:
    """
    Remove stored credentials for the authenticated user.
    """
    deleted = delete_user_credentials(user_id=current_user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Credentials not found")
    return None
