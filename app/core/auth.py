import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.login_service import firebase

logger = logging.getLogger(__name__)
security = HTTPBearer()


def get_current_user_id(creds: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Resolve current user from Bearer token by verifying token via firebase-admin (stateless).
    Legacy in-memory fallback is retained but deprecated.
    """
    token = creds.credentials if creds else None
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    try:
        verified = firebase.verify_id_token(token)
    except Exception:
        logger.exception("Token verification failed")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    if verified and verified.get("user_id"):
        return verified["user_id"]

    # legacy fallback: keep compatibility while clients migrate (deprecated)
    user_id = firebase.get_user_id_by_token(token)
    if user_id:
        logger.warning(
            "Using legacy in-memory token fallback; consider migrating to stateless idTokens"
        )
        return user_id

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
    )
