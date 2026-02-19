from math import log
from venv import logger
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Annotated, Any, Optional

from app.core.netbank.credentials import save_user_credentials, delete_user_credentials
from app.services.login_service import firebase

router = APIRouter(prefix="/netbank", tags=["netbank"])
security = HTTPBearer()  # This is your security scheme

def get_current_user_id(creds: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Resolve the current authenticated user id from the Bearer token.

    Uses the existing Firebase singleton (`firebase`) which maintains an in-memory
    mapping of `idToken` -> `user_id` (see `Firebase.get_user_id_by_token`).
    """
    logger.debug("Resolving current user id from Authorization header: %s", creds)
    token = creds.credentials
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")

    user_id = firebase.get_user_id_by_token(token)
    if not user_id:
        # Token not known in server registry or expired
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return user_id


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
        save_user_credentials(user_id=current_user_id,
                              username=payload.username,
                              account_number=payload.account_number,
                              password=payload.password)
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