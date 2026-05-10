import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, cast

import jwt
import requests
from Crypto.PublicKey import RSA  # nosec B413
from requests import Response, Session

from app.core.firestore_handler.Utils import raise_detailed_error


class Auth:
    """Authentication Service"""

    def __init__(
        self,
        api_key: str,
        requests_session: Optional[Session] = None,
        credentials: Optional[Any] = None,
    ) -> None:
        self.api_key = api_key
        self.current_user: Optional[Dict[str, Any]] = None
        self.requests = requests_session if requests_session is not None else requests
        self.credentials = credentials

    def _base_headers(self, include_header_api_key: bool = True) -> Dict[str, str]:
        headers = {"content-type": "application/json; charset=UTF-8"}
        if include_header_api_key:
            headers["X-Goog-Api-Key"] = self.api_key
        return headers

    def _is_api_key_header_not_supported(self, response: Response) -> bool:
        if response.status_code not in (400, 401, 403):
            return False
        response_text = (response.text or "").lower()
        return "api key" in response_text and (
            "not valid" in response_text
            or "required" in response_text
            or "missing" in response_text
        )

    def _post_with_api_key_mitigation(self, request_ref: str, data: str) -> Response:
        request_object = self.requests.post(
            request_ref,
            headers=self._base_headers(include_header_api_key=True),
            data=data,
        )
        if self._is_api_key_header_not_supported(request_object):
            # Compatibility fallback for endpoints/environments that only accept key query params.
            request_object = self.requests.post(
                f"{request_ref}?key={self.api_key}",
                headers=self._base_headers(include_header_api_key=False),
                data=data,
            )
        return request_object

    def sign_in_with_email_and_password(
        self, email: str, password: str
    ) -> Dict[str, Any]:
        request_ref = (
            "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword"
        )
        data = json.dumps(
            {"email": email, "password": password, "returnSecureToken": True}
        )
        request_object = self._post_with_api_key_mitigation(request_ref, data)
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
            "exp": datetime.now(timezone.utc) + timedelta(minutes=60),
        }
        if additional_claims:
            payload["claims"] = additional_claims
        return jwt.encode(payload, private_key.export_key(), algorithm="RS256")

    def sign_in_with_custom_token(self, token: str) -> Dict[str, Any]:
        request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyCustomToken"
        data = json.dumps({"returnSecureToken": True, "token": token})
        request_object = self._post_with_api_key_mitigation(request_ref, data)
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())

    def refresh(self, refresh_token: str) -> Dict[str, Any]:
        request_ref = "https://securetoken.googleapis.com/v1/token"
        data = json.dumps({"grantType": "refresh_token", "refreshToken": refresh_token})
        request_object = self._post_with_api_key_mitigation(request_ref, data)
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
        )
        data = json.dumps({"idToken": id_token})
        request_object = self._post_with_api_key_mitigation(request_ref, data)
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())

    def send_email_verification(self, id_token: str) -> Dict[str, Any]:
        request_ref = (
            "https://www.googleapis.com/identitytoolkit/v3/relyingparty/"
            "getOobConfirmationCode"
        )
        data = json.dumps({"requestType": "VERIFY_EMAIL", "idToken": id_token})
        request_object = self._post_with_api_key_mitigation(request_ref, data)
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())

    def send_password_reset_email(self, email: str) -> Dict[str, Any]:
        request_ref = (
            "https://www.googleapis.com/identitytoolkit/v3/relyingparty/"
            "getOobConfirmationCode"
        )
        data = json.dumps({"requestType": "PASSWORD_RESET", "email": email})
        request_object = self._post_with_api_key_mitigation(request_ref, data)
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())

    def verify_password_reset_code(
        self, reset_code: str, new_password: str
    ) -> Dict[str, Any]:
        request_ref = (
            "https://www.googleapis.com/identitytoolkit/v3/relyingparty/resetPassword"
        )
        data = json.dumps({"oobCode": reset_code, "newPassword": new_password})
        request_object = self._post_with_api_key_mitigation(request_ref, data)
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())

    def create_user_with_email_and_password(
        self, email: str, password: str
    ) -> Dict[str, Any]:
        request_ref = (
            "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser"
        )
        data = json.dumps(
            {"email": email, "password": password, "returnSecureToken": True}
        )
        request_object = self._post_with_api_key_mitigation(request_ref, data)
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())
