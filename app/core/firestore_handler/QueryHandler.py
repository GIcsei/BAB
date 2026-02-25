import logging
from pathlib import Path
from typing import Dict, Optional

from app.application.services.token_service import TokenService
from app.core.config import get_settings
from app.core.firebase_init import get_project_id
from app.infrastructure.firebase.auth import FirebaseAuthAdapter
from app.infrastructure.firebase.firestore import FirestoreAdapter

logger = logging.getLogger(__name__)

_DEFAULT_FIREBASE = None


class Firebase:
    """
    Lightweight facade that composes Firestore adapter, token service, and auth verifier.
    """

    def __new__(cls, config: Optional[dict] = None):
        if config is None:
            if _DEFAULT_FIREBASE is None:
                raise ValueError(
                    "Firebase not initialized. Call initialize_app(config) during startup."
                )
            return _DEFAULT_FIREBASE
        return super().__new__(cls)

    def __init__(self, config: Optional[dict] = None):
        if getattr(self, "_initialized", False):
            return
        if config is None:
            return

        settings = get_settings()
        self.projectId = config.get("projectId") or get_project_id(allow_default=True)
        self.api_key = config.get("apiKey") or settings.firebase_api_key
        if not self.api_key:
            raise ValueError("FIREBASE_API_KEY is not configured")

        self.firestore_adapter = FirestoreAdapter(self.projectId, self.api_key)
        self.token_service = TokenService(self.api_key, self.firestore_adapter.requests)
        self.auth_adapter = FirebaseAuthAdapter()

        self._initialized = True
        global _DEFAULT_FIREBASE
        _DEFAULT_FIREBASE = self

    def auth(self, token_json: Path):
        return self.token_service.auth(token_json)

    def save_login_token(self, token_data: Dict[str, str]):
        self.token_service.save_login_token(token_data)

    def load_login_token(self) -> Optional[Dict[str, str]]:
        return self.token_service.load_login_token()

    def clear_token(self):
        self.token_service.clear_token()

    def register_user_tokens(
        self,
        user_id: str,
        token: Dict[str, str],
        credentials_path: Optional[Path] = None,
    ) -> None:
        self.token_service.register_user_tokens(user_id, token, credentials_path)

    def load_tokens_from_dir(self, base_dir: Path, refresh: bool = True) -> None:
        self.token_service.load_tokens_from_dir(base_dir, refresh)

    def refresh_token(self, user_id: str) -> Dict[str, str]:
        return self.token_service.refresh_token(user_id)

    def get_user_token(self, user_id: str) -> Optional[Dict[str, str]]:
        return self.token_service.get_user_token(user_id)

    def set_active_user(self, user_id: str) -> Optional[Dict[str, str]]:
        return self.token_service.set_active_user(user_id)

    def clear_user(self, user_id: str) -> None:
        self.token_service.clear_user(user_id)

    def verify_id_token(self, id_token: str) -> Optional[Dict[str, str]]:
        return self.auth_adapter.verify_id_token(id_token)

    def get_user_id_by_token(self, access_token: str) -> Optional[str]:
        return self.token_service.get_user_id_by_token(access_token)

    def database(self):
        return self.firestore_adapter.database()


def initialize_app(config: dict) -> Firebase:
    return Firebase(config)
