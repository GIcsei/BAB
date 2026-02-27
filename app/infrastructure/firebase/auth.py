import logging
from typing import Dict, Optional

from app.core.firebase_init import initialize_firebase_admin, is_testing_env
from firebase_admin import auth as fauth

logger = logging.getLogger(__name__)


class FirebaseAuthAdapter:
    def verify_id_token(self, id_token: str) -> Optional[Dict[str, str]]:
        if not id_token:
            return None

        app = initialize_firebase_admin()
        if app is None and is_testing_env():
            logger.info("Skipping firebase-admin token verification in test mode")
            return None

        try:
            decoded = fauth.verify_id_token(id_token)
            user_id = decoded.get("uid") or decoded.get("user_id")
            if not isinstance(user_id, str):
                return None
            email_value = decoded.get("email")
            email = email_value if isinstance(email_value, str) else ""
            return {
                "user_id": user_id,
                "email": email,
            }
        except Exception:
            logger.exception("Failed to verify id token via firebase-admin")
            return None
