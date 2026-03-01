import json
import requests
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, cast

import jwt
from Crypto.PublicKey import RSA
from requests import Session

from app.core.firestore_handler.Utils import raise_detailed_error


class Auth:
    """Authentication Service"""

    def __init__(
        self,
        api_key: str,
        requests_session: Session,
        credentials: Optional[Any] = None,
    ) -> None:
        self.api_key = api_key
        self.current_user: Optional[Dict[str, Any]] = None
        self.requests = requests_session
        self.credentials = credentials

    def sign_in_with_email_and_password(
        self, email: str, password: str
    ) -> Dict[str, Any]:
        request_ref = (
            "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword"
            f"?key={self.api_key}"
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps(
            {"email": email, "password": password, "returnSecureToken": True}
        )
        request_object = self.requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        payload = cast(Dict[str, Any], request_object.json())
        self.current_user = payload
        return payload

    def create_custom_token(
        self, uid: str, additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        if self.credentials is None:
            raise ValueError("Credentials are required for custom token generation")
        service_account_email = self.credentials.service_account_email
        private_key = RSA.importKey(self.credentials._private_key_pkcs8_pem)
        payload: Dict[str, Any] = {
            "iss": service_account_email,
            "sub": service_account_email,
            "aud": (
                "https://identitytoolkit.googleapis.com/"
                "google.identity.identitytoolkit.v1.IdentityToolkit"
            ),
            "uid": uid,
            "exp": datetime.utcnow() + timedelta(minutes=60),
        }
        if additional_claims:
            payload["claims"] = additional_claims
        return jwt.encode(payload, private_key.export_key(), algorithm="RS256")

    def sign_in_with_custom_token(self, token: str) -> Dict[str, Any]:
        request_ref = (
            "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyCustomToken"
            f"?key={self.api_key}"
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"returnSecureToken": True, "token": token})
        request_object = self.requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())

    def refresh(self, refresh_token: str) -> Dict[str, Any]:
        request_ref = "https://securetoken.googleapis.com/v1/token?key={0}".format(
            self.api_key
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"grantType": "refresh_token", "refreshToken": refresh_token})
        request_object = self.requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        request_object_json = cast(Dict[str, Any], request_object.json())
        user = {
            "userId": request_object_json["user_id"],
            "idToken": request_object_json["id_token"],
            "refreshToken": request_object_json["refresh_token"],
        }
        return user

    def get_account_info(self, id_token: str) -> Dict[str, Any]:
        request_ref = (
            "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getAccountInfo"
            f"?key={self.api_key}"
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"idToken": id_token})
        request_object = self.requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())

    def send_email_verification(self, id_token: str) -> Dict[str, Any]:
        request_ref = (
            "https://www.googleapis.com/identitytoolkit/v3/relyingparty/"
            f"getOobConfirmationCode?key={self.api_key}"
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"requestType": "VERIFY_EMAIL", "idToken": id_token})
        request_object = self.requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())

    def send_password_reset_email(self, email: str) -> Dict[str, Any]:
        request_ref = (
            "https://www.googleapis.com/identitytoolkit/v3/relyingparty/"
            f"getOobConfirmationCode?key={self.api_key}"
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"requestType": "PASSWORD_RESET", "email": email})
        request_object = self.requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())

    def verify_password_reset_code(
        self, reset_code: str, new_password: str
    ) -> Dict[str, Any]:
        request_ref = (
            "https://www.googleapis.com/identitytoolkit/v3/relyingparty/resetPassword"
            f"?key={self.api_key}"
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps({"oobCode": reset_code, "newPassword": new_password})
        request_object = self.requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())

    def create_user_with_email_and_password(
        self, email: str, password: str
    ) -> Dict[str, Any]:
        request_ref = (
            "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser"
            f"?key={self.api_key}"
        )
        headers = {"content-type": "application/json; charset=UTF-8"}
        data = json.dumps(
            {"email": email, "password": password, "returnSecureToken": True}
        )
        request_object = self.requests.post(request_ref, headers=headers, data=data)
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())
