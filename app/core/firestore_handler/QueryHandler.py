import json
import logging
import threading
import asyncio
import os
from pathlib import Path
from typing import Optional, Dict, Any

import requests

from app.core.firestore_handler.User import Auth

logger = logging.getLogger(__name__)

# Application-scoped default instance (set by initialize_app)
_DEFAULT_FIREBASE = None


class TokenPersistence:
    """
    Responsible only for reading/writing per-user token files.
    Provides sync and async helpers. Uses asyncio.to_thread to avoid blocking
    FastAPI event loop when called from async code.
    """

    @staticmethod
    def _read_json(path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception:
            logger.exception("Failed to read token file %s", path)
            return None

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> bool:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return True
        except Exception:
            logger.exception("Failed to write token file %s", path)
            return False

    async def read_json_async(self, path: Path) -> Optional[Dict[str, Any]]:
        return await asyncio.to_thread(self._read_json, path)

    async def write_json_async(self, path: Path, data: Dict[str, Any]) -> bool:
        return await asyncio.to_thread(self._write_json, path, data)

    # Synchronous helpers for non-async callers (keeps backward compatibility)
    def read_json(self, path: Path) -> Optional[Dict[str, Any]]:
        return self._read_json(path)

    def write_json(self, path: Path, data: Dict[str, Any]) -> bool:
        return self._write_json(path, data)


class TokenRegistry:
    """
    Thread-safe in-memory token registry. Keeps per-user token dicts and an
    active (session) token pointer. All mutation guarded by an RLock.
    """

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


def _init_firebase_admin_once(config: Dict[str, Any]) -> None:
    """
    Try to initialize firebase-admin SDK once. Uses GOOGLE_APPLICATION_CREDENTIALS
    if present, otherwise attempts a no-credential init (which still allows token verification).
    Any failure is logged and the code will fall back to the existing Identity Toolkit methods.
    """
    try:
        import firebase_admin
        from firebase_admin import credentials as _cred
    except Exception:
        # firebase-admin not installed or import error; callers will fallback
        logger.debug("firebase-admin not available; will use Identity Toolkit fallback")
        return

    if firebase_admin._apps:
        return

    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    try:
        if cred_path and Path(cred_path).exists():
            cred = _cred.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {"projectId": config.get("projectId")})
            logger.info("Initialized firebase-admin with service account from %s", cred_path)
        else:
            # Initialize without explicit credentials; token verification still works (uses public keys).
            firebase_admin.initialize_app(options={"projectId": config.get("projectId")})
            logger.info("Initialized firebase-admin without explicit service account")
    except Exception:
        logger.exception("Failed to initialize firebase-admin; falling back to Identity Toolkit")


class Firebase:
    """
    Application-scoped Firebase manager.
    - Composes Auth client (API wrapper), TokenPersistence, and TokenRegistry.
    - Does NOT mix persistence and auth responsibilities.
    - Backward-compatible initialize_app(config) sets the module default.
    """

    def __new__(cls, config: Optional[dict] = None):
        # If called without config, return the app-scoped default instance
        if config is None:
            if _DEFAULT_FIREBASE is None:
                raise ValueError(
                    "Firebase not initialized. Call initialize_app(config) during startup."
                )
            return _DEFAULT_FIREBASE
        return super().__new__(cls)

    def __init__(self, config: Optional[dict] = None):
        # Guard re-initialization if default instance already exists
        if getattr(self, "_initialized", False):
            return
        if config is None:
            # should have been returned from __new__ above
            return

        self.api_key = config["apiKey"]
        self.projectId = config.get("projectId")
        self.requests = requests.Session()
        self._auth_client: Optional[Auth] = None
        self._persistence = TokenPersistence()
        self._registry = TokenRegistry()
        self._lock = threading.RLock()  # protects auth client creation
        self.TOKEN_FILE: Optional[Path] = None  # kept for backward compatibility

        # resilient requests session
        for scheme in ("http://", "https://"):
            self.requests.mount(scheme, requests.adapters.HTTPAdapter(max_retries=3))

        # attempt firebase-admin init (best-effort)
        try:
            _init_firebase_admin_once(config)
        except Exception:
            logger.debug("firebase-admin init attempt raised an exception")

        # mark initialized and set module default
        self._initialized = True
        global _DEFAULT_FIREBASE
        _DEFAULT_FIREBASE = self

    # ------ Auth client creation (separate concern) ------
    def _ensure_auth_client(self) -> Auth:
        with self._lock:
            if self._auth_client is None:
                self._auth_client = Auth(self.api_key, self.requests)
            return self._auth_client

    # Backward-compatible API: same signature as previous code
    def auth(self, token_json: Path):
        """
        Return (Auth client, token) like before. Token file handling is minimal here:
        we read the provided token path and attempt a refresh. The persistence layer
        (per-user credentials.json) is handled by TokenPersistence + TokenRegistry.
        """
        auth_client = self._ensure_auth_client()
        self.TOKEN_FILE = token_json
        token = None
        old_token = self.load_login_token()
        if old_token:
            try:
                # keep behavior: attempt refresh; on failure fall back to stored token
                token = auth_client.refresh(old_token.get("refreshToken"))
            except Exception:
                logger.exception(
                    "Failed to refresh token from file; will use stored token"
                )
                token = old_token
        # do not automatically register this token into per-user registry here;
        # login_service should persist/register tokens per-user
        return auth_client, token

    # ----- Backward-compatible persistence helpers (kept small) -----
    def save_login_token(self, token_data: Dict[str, Any]):
        if not self.TOKEN_FILE:
            raise ValueError("TOKEN_FILE is not set for Firebase instance")
        # synchronous write; callers that are async should call the async persistence helper
        self._persistence.write_json(self.TOKEN_FILE, token_data)

    def load_login_token(self) -> Optional[Dict[str, Any]]:
        if not self.TOKEN_FILE:
            return None
        return self._persistence.read_json(self.TOKEN_FILE)

    def clear_token(self):
        if self.TOKEN_FILE and self.TOKEN_FILE.exists():
            try:
                self.TOKEN_FILE.unlink()
            except Exception:
                logger.exception("Failed to clear TOKEN_FILE %s", self.TOKEN_FILE)

    # ----- Per-user registry operations (deterministic lifecycle) -----
    def register_user_tokens(
        self, user_id: str, token: Dict[str, Any], credentials_path: Optional[Path] = None
    ) -> None:
        """
        Register token in-memory and optionally persist to credentials_path.
        Deterministic: register -> optional persist -> set active (explicit).
        """
        self._registry.register(user_id, token)
        if credentials_path:
            try:
                self._persistence.write_json(credentials_path, token)
            except Exception:
                logger.exception("Failed to persist credentials for user %s", user_id)

    def load_tokens_from_dir(self, base_dir: Path, refresh: bool = True) -> None:
        """
        Load per-user credentials found under base_dir/<user_id>/credentials.json.
        Refresh tokens if requested and update the registry and persisted files.
        This method performs I/O and network calls synchronously; call from startup.
        """
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
                logger.warning("No credentials.json found for user directory: %s", child)
                continue

            user_id = child.name
            stored = token_data
            if refresh and stored.get("refreshToken"):
                try:
                    refreshed = auth_client.refresh(stored["refreshToken"])
                    # normalize response
                    normalized = {
                        "userId": refreshed.get("userId")
                        or refreshed.get("user_id")
                        or stored.get("userId"),
                        "idToken": refreshed.get("idToken") or refreshed.get("id_token"),
                        "refreshToken": refreshed.get("refreshToken")
                        or refreshed.get("refresh_token"),
                        "email": stored.get("email"),
                    }
                    stored = normalized
                    # persist refreshed token
                    try:
                        self._persistence.write_json(cred_path, stored)
                    except Exception:
                        logger.debug("Failed to write refreshed token for %s", user_id)
                except Exception:
                    logger.exception("Failed to refresh token for user %s", user_id)
                    # keep the stored token if refresh fails

            self._registry.register(user_id, stored)

    def refresh_token(self, user_id: str) -> Dict[str, Any]:
        """
        Refresh a registered user's tokens deterministically:
        - Require that a token exists for that user
        - Use Auth to refresh and update in-memory + persisted file (if present)
        """
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

        # update registry
        self._registry.register(user_id, normalized)

        # attempt to persist to conventional path (if APP_USER_DATA_DIR is used)
        try:
            # best-effort: persist if we can infer user dir
            from os import getenv

            base = Path(getenv("APP_USER_DATA_DIR", "/var/app/user_data"))
            cred_path = base / user_id / "credentials.json"
            if cred_path.parent.exists():
                self._persistence.write_json(cred_path, normalized)
        except Exception:
            logger.debug("Could not persist refreshed token for %s", user_id)

        return normalized

    def set_active_user(self, user_id: str) -> None:
        """
        Make a user's token the active session token for downstream Firestore calls.
        Deterministic: only succeeds if user is registered.
        """
        self._registry.set_active(user_id)

    def clear_user(self, user_id: str) -> None:
        """Remove user from in-memory registry (no disk deletion)."""
        self._registry.remove(user_id)

    def verify_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify ID token using firebase-admin if available; fallback to Identity Toolkit
        via Auth.get_account_info for environments without firebase-admin.
        Returns normalized payload or None.
        """
        if not id_token:
            return None

        # Try firebase-admin verification first (stateless, recommended)
        try:
            import firebase_admin
            from firebase_admin import auth as _fauth
        except Exception:
            firebase_admin = None
            _fauth = None

        if firebase_admin and _fauth:
            try:
                # verify_id_token raises on invalid/expired tokens
                decoded = _fauth.verify_id_token(id_token)
                # uid is the canonical user id (localId)
                return {"user_id": decoded.get("uid") or decoded.get("user_id"), "email": decoded.get("email")}
            except Exception:
                logger.exception("firebase-admin failed to verify id token; will fallback")

        # Fallback: use Identity Toolkit via Auth client (network call)
        try:
            info = self._ensure_auth_client().get_account_info(id_token)
            users = info.get("users") if isinstance(info, dict) else None
            if not users:
                return None
            user = users[0] or {}
            return {
                "user_id": user.get("localId") or user.get("userId") or user.get("uid"),
                "email": user.get("email"),
            }
        except Exception:
            logger.exception("Fallback verification failed")
            return None

    def get_user_id_by_token(self, access_token: str) -> Optional[str]:
        """
        Legacy helper: searches the in-memory registry for an idToken match.
        Kept for backward compatibility but not used for primary request auth.
        """
        return self._registry.find_user_by_id_token(access_token)


def initialize_app(config: dict) -> Firebase:
    """
    Initialize and return the application-scoped Firebase manager.
    Call this during FastAPI startup (e.g. in app.main) and avoid calling
    Firebase() without config directly thereafter.
    """
    return Firebase(config)
