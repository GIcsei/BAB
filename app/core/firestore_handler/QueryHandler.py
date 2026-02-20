import json
import logging
from pathlib import Path

import requests

from app.core.firestore_handler.FirestoreService import FirestoreService
from app.core.firestore_handler.User import Auth

logger = logging.getLogger(__name__)


def initialize_app(config):
    return Firebase(config)


class Firebase:
    """Firebase Interface"""

    _instance = None
    _database = None
    _auth_instance = None

    def __new__(cls, config=None):
        if cls._instance is not None:
            return cls._instance
        if config is None:
            raise ValueError("Cannot create instance as config was not given!")
        cls._instance = super().__new__(cls)
        cls._instance._initialize(config)
        return cls._instance

    def _initialize(self, config):
        self.api_key = config["apiKey"]
        self.projectId = config["projectId"]
        self.requests = requests.Session()
        self.token = None
        self.user_tokens = {}  # in-memory mapping: user_id -> token dict
        for scheme in ("http://", "https://"):
            self.requests.mount(scheme, requests.adapters.HTTPAdapter(max_retries=3))

    def auth(self, token_json: Path):
        if self._auth_instance is None:
            self._auth_instance = Auth(self.api_key, self.requests)
        token = None
        self.TOKEN_FILE = token_json
        old_token = self.load_login_token()
        if old_token:
            try:
                token = self._auth_instance.refresh(old_token["refreshToken"])
            except Exception:
                token = old_token
        self.token = token
        return self._auth_instance, token

    def clear_token(self):
        if hasattr(self, "TOKEN_FILE") and self.TOKEN_FILE.exists():
            self.TOKEN_FILE.unlink()

    def save_login_token(self, token_data):
        # save to the currently set TOKEN_FILE path
        if not hasattr(self, "TOKEN_FILE"):
            raise ValueError("TOKEN_FILE is not set for Firebase instance")
        with open(self.TOKEN_FILE, "w") as f:
            json.dump(token_data, f)

    def load_login_token(self):
        if not hasattr(self, "TOKEN_FILE"):
            return None
        if self.TOKEN_FILE.exists():
            with open(self.TOKEN_FILE, "r") as f:
                return json.load(f)
        return None

    def database(self):
        if self._auth_instance is None:
            raise ValueError(
                "No instance of AUTH had been made yet! Cannot join to database..."
            )
        if self._database is None:
            self._database = FirestoreService(self)
        return self._database

    # --- new helpers for per-user token management ---

    def load_tokens_from_dir(self, base_dir: Path, refresh: bool = True):
        """
        Scan base_dir for per-user credential files and load them into self.user_tokens.
        Optionally try to refresh tokens using the Auth client.
        """
        base_dir = Path(base_dir)
        if not base_dir.exists():
            return

        if self._auth_instance is None:
            self._auth_instance = Auth(self.api_key, self.requests)

        for child in base_dir.iterdir():
            if not child.is_dir():
                continue
            cred_path = child / "credentials.json"
            if not cred_path.exists():
                continue
            try:
                with open(cred_path, "r", encoding="utf-8") as f:
                    token_data = json.load(f)
            except Exception:
                continue

            user_id = child.name
            stored = token_data
            # try refresh to obtain a fresh idToken if possible
            if refresh and stored.get("refreshToken"):
                try:
                    refreshed = self._auth_instance.refresh(stored["refreshToken"])
                    # normalize refreshed dict
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
                    # write back refreshed token to credentials.json
                    try:
                        with open(cred_path, "w", encoding="utf-8") as f:
                            json.dump(stored, f)
                    except Exception:
                        pass
                except Exception:
                    # keep the stored token if refresh fails
                    logger.exception("Failed to refresh token for user %s", user_id)

            self.user_tokens[user_id] = stored

    def set_active_user(self, user_id: str):
        """
        Set the singleton active token for Firestore calls.
        """
        token = self.user_tokens.get(user_id)
        if not token:
            raise ValueError(f"No token registered for user {user_id}")
        self.token = token

    def clear_user(self, user_id: str):
        """
        Remove user from in-memory registry. Does not delete files on disk.
        """
        self.user_tokens.pop(user_id, None)
        # If the active token pointed to this user, unset it
        if self.token and (
            self.token.get("userId") == user_id
            or self.token.get("idToken")
            == self.user_tokens.get(user_id, {}).get("idToken")
        ):
            self.token = None

    def verify_id_token(self, id_token: str):
        """
        Verify an ID token through Identity Toolkit and return normalized identity payload.
        Returns {"user_id": "...", "email": "..."} or None if invalid.
        """
        if not id_token:
            return None
        if self._auth_instance is None:
            self._auth_instance = Auth(self.api_key, self.requests)
        try:
            info = self._auth_instance.get_account_info(id_token)
            users = info.get("users") if isinstance(info, dict) else None
            if not users:
                return None
            user = users[0] or {}
            return {
                "user_id": user.get("localId") or user.get("userId") or user.get("uid"),
                "email": user.get("email"),
            }
        except Exception:
            logger.exception("Failed to verify id token")
            return None

    def get_user_id_by_token(self, access_token: str):
        for uid, tok in self.user_tokens.items():
            if tok.get("idToken") == access_token:
                return uid
        return None


# Example usage
if __name__ == "__main__":
    # User credentials
    email = "icseig@outlook.hu"  # Replace with a test email
    password = "yourpassword"  # Replace with a strong password
    # Replace these with your actual Firebase project settings
    config = {
        "apiKey": "AIzaSyC9rGGx4XNmOXqZCi8ni9B8NkylFtdRbS4",
        "authDomain": "ersterepgen.firebaseapp.com",
        "databaseURL": "https://ersterepgen.firebaseio.com/",
        "storageBucket": "ersterepgen.firebasestorage.app",
        "projectId": "ersterepgen",
    }
    token = None
    # Data for the POST request to Firebase Authentication REST API
    data = {"email": email, "password": password, "returnSecureToken": True}

    # 🔹 Initialize Firebase Authentication (Pyrebase)
    firebase = initialize_app(config)
    auth_client, result = firebase.auth(Path("auth_token.json"))
    db = firebase.database()

    if not result:
        logger.info("Signing in again...")
        result = auth_client.sign_in_with_email_and_password(email, password)
    logger.info(db.get_document("users"))

    # db.child("messages").push(data={},token = result["idToken"])
    changed_doc = db.run_query("messages", f'uid == {result["userId"]}')
    logger.info(changed_doc)
    timeStamp = 1745015393000
    changed_doc = db.run_query(
        "messages", f'uid == {result["userId"]} AND timestamp >= {timeStamp}'
    )

    logger.info("\n\n\n")
    data = db.get_document("messages")
    logger.info(data.sort_by("timestamp"))
