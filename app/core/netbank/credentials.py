import os
import json
import base64
import hashlib
import logging
from typing import Optional, Dict

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception as exc:
    raise ImportError(
        "cryptography is required for encrypted credential storage. Install with: pip install cryptography"
    ) from exc

logger = logging.getLogger(__name__)

# Tag ties the credential blob to the ErsteNetBroker class.
_CLASS_TAG = "app.core.netbank.getReport.ErsteNetBroker"

# Default storage location under the service account user's config directory
_DEFAULT_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "bank_analysis")


def _ensure_config_dir(config_dir: str) -> None:
    os.makedirs(config_dir, exist_ok=True)
    try:
        os.chmod(config_dir, 0o700)
    except Exception:
        logger.debug("chmod not supported for %s", config_dir)


def _hash_tag(tag: str) -> str:
    return hashlib.sha256(tag.encode("utf-8")).hexdigest()[:16]


def _key_path_for_dir(config_dir: str) -> str:
    # single key per class (used to encrypt all per-user blobs if no master key env is set)
    return os.path.join(config_dir, f"key_{_hash_tag(_CLASS_TAG)}.key")


def _cred_path_for_dir(config_dir: str, user_id: str) -> str:
    safe_user = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]
    return os.path.join(config_dir, f"cred_{safe_user}_{_hash_tag(_CLASS_TAG)}.json")


def _ensure_key(config_dir: str) -> bytes:
    """
    Ensure a Fernet key exists for the class and return the raw key bytes.
    If operator set NETBANK_MASTER_KEY in env, it will be used instead.
    """
    env_key = os.environ.get("NETBANK_MASTER_KEY")
    if env_key:
        try:
            # Accept either raw urlsafe_b64 key or plain text; prefer urlsafe_b64
            key_bytes = env_key.encode("utf-8")
            # validate key length by attempting to instantiate
            Fernet(key_bytes)
            return key_bytes
        except Exception:
            # try decode as plaintext -> generate stable key from it
            key = base64.urlsafe_b64encode(hashlib.sha256(env_key.encode("utf-8")).digest())
            return key

    key_path = _key_path_for_dir(config_dir)
    if os.path.exists(key_path):
        with open(key_path, "rb") as fh:
            return fh.read()
    key = Fernet.generate_key()
    # Write with restrictive permissions
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(key_path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(key)
    except Exception:
        try:
            with open(key_path, "wb") as fh:
                fh.write(key)
            os.chmod(key_path, 0o600)
        except Exception:
            logger.exception("Failed to write key file %s", key_path)
            raise
    return key


def save_user_credentials(user_id: str, username: str, account_number: str, password: str,
                          config_dir: Optional[str] = None) -> None:
    """
    Save credentials for a given user_id encrypted and tagged for ErsteNetBroker.
    Creates per-user credential file with restrictive permissions.
    """
    if not user_id:
        raise ValueError("user_id is required")

    if config_dir is None:
        config_dir = _DEFAULT_CONFIG_DIR
    _ensure_config_dir(config_dir)

    key = _ensure_key(config_dir)
    f = Fernet(key)

    payload = json.dumps({
        "class": _CLASS_TAG,
        "user_id": user_id,
        "username": username,
        "account_number": account_number,
        "password": password
    }).encode("utf-8")

    token = f.encrypt(payload)
    token_b64 = base64.urlsafe_b64encode(token).decode("utf-8")

    cred_blob = {
        "class": _CLASS_TAG,
        "user_id": user_id,
        "token": token_b64
    }

    cred_path = _cred_path_for_dir(config_dir, user_id)
    # write with restrictive permissions
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(cred_path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(cred_blob, fh)
    except Exception:
        try:
            with open(cred_path, "w", encoding="utf-8") as fh:
                json.dump(cred_blob, fh)
            os.chmod(cred_path, 0o600)
        except Exception:
            logger.exception("Failed to write credential file %s", cred_path)
            raise


def load_user_credentials(user_id: str, config_dir: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    Load and decrypt credentials stored for the given user_id.
    Returns dict with keys: username, account_number, password or None if not available or invalid.
    """
    if not user_id:
        return None
    if config_dir is None:
        config_dir = _DEFAULT_CONFIG_DIR

    cred_path = _cred_path_for_dir(config_dir, user_id)
    if not os.path.exists(cred_path):
        logger.debug("Credential file not present for user %s in %s", user_id, config_dir)
        return None

    try:
        with open(cred_path, "r", encoding="utf-8") as fh:
            cred_blob = json.load(fh)
    except Exception:
        logger.exception("Failed to read credential file %s", cred_path)
        return None

    if cred_blob.get("class") != _CLASS_TAG or cred_blob.get("user_id") != user_id:
        logger.warning("Credential file tags do not match expected values for user %s", user_id)
        return None

    token_b64 = cred_blob.get("token")
    if not token_b64:
        logger.warning("Credential file missing token for user %s", user_id)
        return None

    try:
        token = base64.urlsafe_b64decode(token_b64.encode("utf-8"))
    except Exception:
        logger.exception("Failed to decode token from credential file for user %s", user_id)
        return None

    try:
        key = _ensure_key(config_dir)
    except Exception:
        logger.exception("Failed to obtain encryption key")
        return None

    try:
        f = Fernet(key)
        payload = f.decrypt(token)
    except InvalidToken:
        logger.warning("Invalid token or wrong key while decrypting credentials for user %s", user_id)
        return None
    except Exception:
        logger.exception("Error while decrypting credentials for user %s", user_id)
        return None

    try:
        data = json.loads(payload.decode("utf-8"))
        if data.get("class") != _CLASS_TAG or data.get("user_id") != user_id:
            logger.warning("Decrypted payload tag mismatch for user %s", user_id)
            return None
        return {
            "username": data.get("username"),
            "account_number": data.get("account_number"),
            "password": data.get("password")
        }
    except Exception:
        logger.exception("Failed to parse decrypted credential payload for user %s", user_id)
        return None


def delete_user_credentials(user_id: str, config_dir: Optional[str] = None) -> bool:
    """
    Remove stored credentials for a user. Returns True if file removed.
    """
    if not user_id:
        return False
    if config_dir is None:
        config_dir = _DEFAULT_CONFIG_DIR
    cred_path = _cred_path_for_dir(config_dir, user_id)
    try:
        if os.path.exists(cred_path):
            os.remove(cred_path)
            return True
    except Exception:
        logger.exception("Failed to delete credential file %s", cred_path)
    return False