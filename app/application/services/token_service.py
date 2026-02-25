import asyncio
import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.core.firestore_handler.User import Auth

logger = logging.getLogger(__name__)


class TokenPersistence:
    @staticmethod
    def _read_json(path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to read token file %s", path)
            return None

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> bool:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as file:
                json.dump(data, file)
            return True
        except Exception:
            logger.exception("Failed to write token file %s", path)
            return False

    async def read_json_async(self, path: Path) -> Optional[Dict[str, Any]]:
        return await asyncio.to_thread(self._read_json, path)

    async def write_json_async(self, path: Path, data: Dict[str, Any]) -> bool:
        return await asyncio.to_thread(self._write_json, path, data)

    def read_json(self, path: Path) -> Optional[Dict[str, Any]]:
        return self._read_json(path)

    def write_json(self, path: Path, data: Dict[str, Any]) -> bool:
        return self._write_json(path, data)


class TokenRegistry:
    def __init__(self):
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._active_user: Optional[str] = None
        self._lock = threading.RLock()

    def register(self, user_id: str, token_data: Dict[str, Any]) -> None:
        with self._lock:
            self._tokens[user_id] = dict(token_data)

    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            token = self._tokens.get(user_id)
            return dict(token) if token is not None else None

    def remove(self, user_id: str) -> None:
        with self._lock:
            self._tokens.pop(user_id, None)
            if self._active_user == user_id:
                self._active_user = None

    def set_active(self, user_id: str) -> None:
        with self._lock:
            if user_id not in self._tokens:
                raise ValueError(f"No token registered for user {user_id}")
            self._active_user = user_id

    def get_active_token(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if self._active_user:
                return dict(self._tokens.get(self._active_user))
            return None

    def find_user_by_id_token(self, id_token: str) -> Optional[str]:
        with self._lock:
            for uid, tok in self._tokens.items():
                if tok.get("idToken") == id_token:
                    return uid
        return None


class TokenService:
    def __init__(self, api_key: str, requests_session):
        self._registry = TokenRegistry()
        self._persistence = TokenPersistence()
        self._lock = threading.RLock()
        self._token_file: Optional[Path] = None
        self._auth_client: Optional[Auth] = None
        self._requests = requests_session
        self._api_key = api_key

    def _ensure_auth_client(self) -> Auth:
        with self._lock:
            if self._auth_client is None:
                self._auth_client = Auth(self._api_key, self._requests)
            return self._auth_client

    def auth(self, token_json: Path):
        auth_client = self._ensure_auth_client()
        self._token_file = token_json
        token = None
        existing = self.load_login_token()
        if existing:
            try:
                token = auth_client.refresh(existing.get("refreshToken"))
            except Exception:
                logger.exception(
                    "Failed to refresh token from file; using stored token"
                )
                token = existing
        return auth_client, token

    def save_login_token(self, token_data: Dict[str, Any]):
        if not self._token_file:
            raise ValueError("TOKEN_FILE is not set for TokenService instance")
        self._persistence.write_json(self._token_file, token_data)

    def load_login_token(self) -> Optional[Dict[str, Any]]:
        if not self._token_file:
            return None
        return self._persistence.read_json(self._token_file)

    def clear_token(self):
        if self._token_file and self._token_file.exists():
            try:
                self._token_file.unlink()
            except Exception:
                logger.exception("Failed to clear TOKEN_FILE %s", self._token_file)

    def register_user_tokens(
        self,
        user_id: str,
        token: Dict[str, Any],
        credentials_path: Optional[Path] = None,
    ) -> None:
        self._registry.register(user_id, token)
        if credentials_path:
            try:
                self._persistence.write_json(credentials_path, token)
            except Exception:
                logger.exception("Failed to persist credentials for user %s", user_id)

    def load_tokens_from_dir(self, base_dir: Path, refresh: bool = True) -> None:
        base_dir = Path(base_dir)
        if not base_dir.exists():
            logger.info("Base directory for user tokens does not exist: %s", base_dir)
            return

        auth_client = self._ensure_auth_client()

        for child in base_dir.iterdir():
            if not child.is_dir():
                continue
            cred_path = child / "credentials.json"
            token_data = self._persistence.read_json(cred_path)
            if not token_data:
                logger.warning(
                    "No credentials.json found for user directory: %s", child
                )
                continue

            user_id = child.name
            stored = token_data
            if refresh and stored.get("refreshToken"):
                try:
                    refreshed = auth_client.refresh(stored["refreshToken"])
                    normalized = {
                        "userId": refreshed.get("userId")
                        or refreshed.get("user_id")
                        or stored.get("userId"),
                        "idToken": refreshed.get("idToken")
                        or refreshed.get("id_token"),
                        "refreshToken": refreshed.get("refreshToken")
                        or refreshed.get("refresh_token"),
                        "email": stored.get("email"),
                    }
                    stored = normalized
                    try:
                        self._persistence.write_json(cred_path, stored)
                    except Exception:
                        logger.debug("Failed to write refreshed token for %s", user_id)
                except Exception:
                    logger.exception("Failed to refresh token for user %s", user_id)

            self._registry.register(user_id, stored)

    def refresh_token(self, user_id: str) -> Dict[str, Any]:
        token = self._registry.get(user_id)
        if not token:
            raise ValueError(f"No token found for user {user_id} to refresh")

        auth_client = self._ensure_auth_client()
        refreshed = auth_client.refresh(token["refreshToken"])
        normalized = {
            "userId": refreshed.get("userId")
            or refreshed.get("user_id")
            or token.get("userId"),
            "idToken": refreshed.get("idToken") or refreshed.get("id_token"),
            "refreshToken": refreshed.get("refreshToken")
            or refreshed.get("refresh_token"),
            "email": token.get("email"),
        }

        self._registry.register(user_id, normalized)

        try:
            base = get_settings().app_user_data_dir
            cred_path = base / user_id / "credentials.json"
            if cred_path.parent.exists():
                self._persistence.write_json(cred_path, normalized)
        except Exception:
            logger.debug("Could not persist refreshed token for %s", user_id)

        return normalized

    def get_user_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._registry.get(user_id)

    def set_active_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        token = self._registry.get(user_id)
        if not token:
            raise ValueError(f"No token registered for user {user_id}")
        self._registry.set_active(user_id)
        return token

    def clear_user(self, user_id: str) -> None:
        self._registry.remove(user_id)

    def get_user_id_by_token(self, access_token: str) -> Optional[str]:
        return self._registry.find_user_by_id_token(access_token)
