# FirestoreService.py

import json
from functools import wraps
from typing import Optional, Dict, Any

from app.core.firestore_handler.DataDescriptor import Collection, Document
from app.core.firestore_handler.Query import FirestoreQueryBuilder
from app.core.firestore_handler.Utils import raise_detailed_error


def deserialize_response(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        response_dict = {}
        result = None
        if isinstance(response, list):
            response_dict["documents"] = response
        else:
            response_dict = response

        if response_dict.get("documents"):
            result = Collection.from_list("", response_dict["documents"])
        else:
            result = Collection("")
            result.add_doc(Document.from_dict(response))

        if result is None:
            raise ValueError(
                f"No answer had been received, document cannot be created on: {response}!"
            )

        return result

    return wrapper


class FirestoreService:
    def __init__(self, firebase):
        # keep reference to Firebase instance so config is visible
        self.firebase = firebase
        self.base_url = f"https://firestore.googleapis.com/v1/projects/{firebase.projectId}/databases/(default)/documents"
        self.api_key = firebase.api_key
        self.requests = firebase.requests

    def _build_headers(self, token: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json; charset=UTF-8"}
        if token is not None:
            # token is expected to be a dict with 'idToken'
            headers["Authorization"] = f"Bearer {token.get('idToken')}"
        return headers

    def _build_url(self, path: str):
        if "runQuery" in path:  # query request, special handling
            return f"{self.base_url}:runQuery"
        correct_path = path[1:] if path.startswith("/") else path
        return f"{self.base_url}/{correct_path}"

    @deserialize_response
    def get_document(self, path: str, token: Optional[Dict[str, Any]] = None):
        url = self._build_url(path)
        response = self.requests.get(url, headers=self._build_headers(token))
        raise_detailed_error(response)
        return response.json()

    def set_document(self, path: str, data: Dict[str, Any], token: Optional[Dict[str, Any]] = None):
        url = self._build_url(path)
        response = self.requests.put(url, headers=self._build_headers(token), data=json.dumps(data))
        raise_detailed_error(response)
        return response.json()

    def update_document(self, path: str, data: Dict[str, Any], token: Optional[Dict[str, Any]] = None):
        url = self._build_url(path)
        response = self.requests.patch(url, headers=self._build_headers(token), data=json.dumps(data))
        raise_detailed_error(response)
        return response.json()

    def delete_document(self, path: str, token: Optional[Dict[str, Any]] = None):
        url = self._build_url(path)
        response = self.requests.delete(url, headers=self._build_headers(token))
        raise_detailed_error(response)
        return response.json()

    def create_document(self, path: str, data: Dict[str, Any], token: Optional[Dict[str, Any]] = None):
        url = self._build_url(path)
        response = self.requests.post(url, headers=self._build_headers(token), data=json.dumps(data))
        raise_detailed_error(response)
        return response.json()

    @deserialize_response
    def run_query(self, collection: str, query_string: str, token: Optional[Dict[str, Any]] = None):
        url = self._build_url("runQuery")
        query_payload = FirestoreQueryBuilder(collection).build_query(query_string)
        response = self.requests.post(url, headers=self._build_headers(token), data=json.dumps(query_payload))
        raise_detailed_error(response)
        return response.json()
