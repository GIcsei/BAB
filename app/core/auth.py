import logging
from typing import Optional, cast

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.error_mapping import exception_to_http
from app.core.exceptions import InvalidTokenError, MissingTokenError
from app.core.firestore_handler.QueryHandler import Firebase

logger = logging.getLogger(__name__)
security = HTTPBearer()

def get_firebase_dep(request: Request) -> Firebase:
    """Dependency to retrieve the Firebase instance from app state, with error handling if not available."""
    firebase = cast(Optional[Firebase], getattr(request.app.state, "firebase", None))
    if firebase is None:
        raise HTTPException(status_code=503, detail="Firebase unavailable")
    return firebase


def get_current_user_id(
    creds: HTTPAuthorizationCredentials = Depends(security),
    firebase: Firebase = Depends(get_firebase_dep),
) -> str:
    token = creds.credentials if creds else None
    if not token:
        raise exception_to_http(MissingTokenError())

    try:
        verified = firebase.verify_id_token(token)
    except Exception:
        logger.exception("Token verification failed")
        raise exception_to_http(InvalidTokenError())

    if verified and verified.get("user_id"):
        logger.debug("Token verified successfully for user_id: %s", verified["user_id"])
        return verified["user_id"]

    logger.warning("Token verification did not return user_id; checking legacy token registry")
    user_id = firebase.get_user_id_by_token(token)
    if user_id:
        logger.warning(
            "Using legacy in-memory token fallback; consider migrating to stateless idTokens"
        )
        return user_id

    logger.error("Token verification failed and no legacy token found for token: %s", token)
    raise exception_to_http(InvalidTokenError())
