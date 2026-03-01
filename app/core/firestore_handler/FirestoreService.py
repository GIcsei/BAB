# FirestoreService.py
import logging
import json
from functools import wraps
from typing import Any, Callable, Dict, Optional, Protocol, Union, cast

from requests import Session

from app.core.firestore_handler.DataDescriptor import Collection, Document
from app.core.firestore_handler.Query import FirestoreQueryBuilder
from app.core.firestore_handler.Utils import raise_detailed_error

ResponsePayload = Union[Dict[str, Any], list[Dict[str, Any]]]


class _FirebaseProtocol(Protocol):
    projectId: str
    api_key: str
    requests: Session


def deserialize_response(
    func: Callable[..., ResponsePayload],
) -> Callable[..., Collection]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Collection:
        response = func(*args, **kwargs)
        response_dict: Dict[str, Any] = {}
        if isinstance(response, list):
            response_dict["documents"] = response
        else:
            response_dict = response

        if response_dict.get("documents"):
            result = Collection.from_list("", response_dict["documents"])
        else:
            result = Collection("")
            result.add_doc(Document.from_dict(response_dict))

        return result

    return wrapper


class FirestoreService:
    def __init__(self, firebase: _FirebaseProtocol) -> None:
        self.firebase = firebase
        self.base_url = (
            "https://firestore.googleapis.com/v1/projects/"
            f"{firebase.projectId}/databases/(default)/documents"
        )
        self.api_key = firebase.api_key
        self.requests = firebase.requests
        self.logger = logging.get_logger(__name__)

    def _build_headers(self, token: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json; charset=UTF-8"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token.get('idToken')}"
        return headers

    def _build_url(self, path: str) -> str:
        if "runQuery" in path:
            return f"{self.base_url}:runQuery"
        correct_path = path[1:] if path.startswith("/") else path
        return f"{self.base_url}/{correct_path}"

    @deserialize_response
    def get_document(
        self, path: str, token: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = self._build_url(path)
        response = self.requests.get(url, headers=self._build_headers(token))
        raise_detailed_error(response)
        return cast(Dict[str, Any], response.json())

    def set_document(
        self, path: str, data: Dict[str, Any], token: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = self._build_url(path)
        response = self.requests.put(
            url, headers=self._build_headers(token), data=json.dumps(data)
        )
        raise_detailed_error(response)
        return cast(Dict[str, Any], response.json())

    def update_document(
        self, path: str, data: Dict[str, Any], token: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = self._build_url(path)
        response = self.requests.patch(
            url, headers=self._build_headers(token), data=json.dumps(data)
        )
        raise_detailed_error(response)
        return cast(Dict[str, Any], response.json())

    def delete_document(
        self, path: str, token: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = self._build_url(path)
        response = self.requests.delete(url, headers=self._build_headers(token))
        raise_detailed_error(response)
        return cast(Dict[str, Any], response.json())

    def create_document(
        self, path: str, data: Dict[str, Any], token: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = self._build_url(path)
        response = self.requests.post(
            url, headers=self._build_headers(token), data=json.dumps(data)
        )
        raise_detailed_error(response)
        return cast(Dict[str, Any], response.json())

    @deserialize_response
    def run_query(
        self, collection: str, query_string: str, token: Optional[Dict[str, Any]] = None
    ) -> list[Dict[str, Any]]:
        url = self._build_url("runQuery")
        query_payload = FirestoreQueryBuilder(collection).build_query(query_string)
        response = self.requests.post(
            url, headers=self._build_headers(token), data=json.dumps(query_payload)
        )
        self.logger.debug("Received response: %s", response.json())
        raise_detailed_error(response)
        return cast(list[Dict[str, Any]], response.json())
