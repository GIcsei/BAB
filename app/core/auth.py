import logging

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.error_mapping import exception_to_http
from app.core.exceptions import (
    InvalidTokenError,
    MissingTokenError,
)
from app.services.login_service import firebase

logger = logging.getLogger(__name__)
security = HTTPBearer()


def get_current_user_id(creds: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Resolve current user from Bearer token by verifying token via firebase-admin (stateless).
    Raises typed exceptions for narrow error handling.
    """
    token = creds.credentials if creds else None
    if not token:
        raise exception_to_http(MissingTokenError())

    try:
        verified = firebase.verify_id_token(token)
    except Exception:
        logger.exception("Token verification failed")
        raise exception_to_http(InvalidTokenError())

    if verified and verified.get("user_id"):
        return verified["user_id"]

    # legacy fallback: keep compatibility while clients migrate (deprecated)
    user_id = firebase.get_user_id_by_token(token)
    if user_id:
        logger.warning(
            "Using legacy in-memory token fallback; consider migrating to stateless idTokens"
        )
        return user_id

    raise exception_to_http(InvalidTokenError())
