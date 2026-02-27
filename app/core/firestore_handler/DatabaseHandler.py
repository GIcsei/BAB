import json
import logging
import math
import time
from random import uniform
from typing import Any, Dict, Optional, cast
from urllib.parse import quote

from app.core.firestore_handler.DataDescriptor import Collection, Document
from app.core.firestore_handler.Query import FirestoreQueryBuilder
from app.core.firestore_handler.QueryHandler import Firebase
from app.core.firestore_handler.Utils import Stream, raise_detailed_error

logger = logging.getLogger(__name__)


class Database:
    """Database Service"""

    def __init__(self) -> None:
        fb = Firebase()
        self.fb = fb
        self.database_url = (
            "https://firestore.googleapis.com/v1/projects/"
            f"{fb.projectId}/databases/(default)/documents"
        )
        self.requests = fb.requests
        self.key = fb.api_key
        self.path = ""
        self.build_query: Dict[str, Any] = {}
        self.last_push_time = 0
        self.last_rand_chars: list[int] = []

    def order_by_key(self) -> "Database":
        self.build_query["orderBy"] = "$key"
        return self

    def order_by_value(self) -> "Database":
        self.build_query["orderBy"] = "$value"
        return self

    def order_by_field(self, order: str) -> "Database":
        self.build_query["orderBy"] = order
        return self

    def start_at(self, start: Any) -> "Database":
        self.build_query["startAt"] = start
        return self

    def end_at(self, end: Any) -> "Database":
        self.build_query["endAt"] = end
        return self

    def equal_to(self, equal: Any) -> "Database":
        self.build_query["equalTo"] = equal
        return self

    def limit_to_first(self, limit_first: int) -> "Database":
        self.build_query["limitToFirst"] = limit_first
        return self

    def limit_to_last(self, limit_last: int) -> "Database":
        self.build_query["limitToLast"] = limit_last
        return self

    def listDocuments(self, token: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if token is None:
            token = self.fb.token
        header = self.build_headers(token)
        url = self.build_request_url()
        response = self.requests.get(url=url, headers=header)
        raise_detailed_error(response)
        return cast(Dict[str, Any], response.json())

    def addStringQuery(self, query: str) -> "Database":
        self.build_query["StringQuery"] = query
        self.path = ":runQuery"
        return self

    def child(self, *args: str) -> "Database":
        new_path = "/".join([str(arg) for arg in args])
        if not self.path:
            self.path = ""
        self.path += "/{}".format(new_path)
        return self

    def build_request_url(self) -> str:
        parameters: Dict[str, Any] = {}
        for param in list(self.build_query):
            if type(self.build_query[param]) is str:
                parameters[param] = quote('"' + self.build_query[param] + '"')
            elif type(self.build_query[param]) is bool:
                parameters[param] = "true" if self.build_query[param] else "false"
            else:
                parameters[param] = self.build_query[param]
        request_ref = "{0}{1}".format(self.database_url, self.path)
        return request_ref

    def build_headers(self, token: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        headers = {"content-type": "application/json; charset=UTF-8"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token['idToken']}"
        return headers

    def _request(
        self,
        token: Optional[Dict[str, Any]],
        json_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if json_kwargs is None:
            json_kwargs = {}
        request_ref = self.build_request_url()
        if token is None:
            token = self.fb.token
        headers = self.build_headers(token)
        if self.build_query.get("StringQuery"):
            request_object = self.requests.post(
                request_ref,
                headers=headers,
                data=json.dumps(
                    FirestoreQueryBuilder("messages").build_query(
                        self.build_query["StringQuery"]
                    )
                ),
            )
        else:
            request_object = self.requests.get(request_ref, headers=headers)
        self.path = ""
        self.build_query = {}
        raise_detailed_error(request_object)
        return request_object.json(**json_kwargs)

    def filtering(
        self, response_dict: Collection, filters: Dict[str, Any]
    ) -> Collection:
        for key, value in filters.items():
            if key == "limitToFirst":
                response_dict.update_elems(slice(0, value))
            if key == "limitToLast":
                max_index = len(response_dict.documents) - 1
                response_dict.update_elems(slice(max_index - value, max_index))
            if key == "orderBy":
                response_dict.sort_by(value)
            logger.warning(
                "Can't found element for filter setting: %s : %s", key, value
            )
        return response_dict

    def get(
        self,
        token: Optional[Dict[str, Any]] = None,
        json_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Collection:
        if token is None:
            token = self.fb.token
        build_query = self.build_query
        query_key = self.path.split("/")[-1]

        request_dict = self._request(token, json_kwargs)

        if isinstance(request_dict, list):
            request_dict = {"documents": request_dict}

        response_dict: Optional[Collection] = None
        if request_dict.get("documents"):
            response_dict = Collection.from_list(query_key, request_dict["documents"])
        if not isinstance(response_dict, Collection):
            response_dict = Collection(query_key)
            response_dict.add_doc(Document.from_dict(request_dict))

        if build_query:
            response_dict = self.filtering(response_dict, build_query)

        return response_dict

    def push(
        self,
        data: Dict[str, Any],
        token: Optional[Dict[str, Any]] = None,
        json_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if json_kwargs is None:
            json_kwargs = {}
        if token is None:
            token = self.fb.token
        request_ref = self.build_request_url()
        self.path = ""
        headers = self.build_headers(token)
        request_object = self.requests.post(
            request_ref,
            headers=headers,
            data=json.dumps(data, **json_kwargs).encode("utf-8"),
        )
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())

    def set(
        self,
        data: Dict[str, Any],
        token: Optional[Dict[str, Any]] = None,
        json_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if json_kwargs is None:
            json_kwargs = {}
        if token is None:
            token = self.fb.token
        request_ref = self.build_request_url()
        self.path = ""
        headers = self.build_headers(token)
        request_object = self.requests.put(
            request_ref,
            headers=headers,
            data=json.dumps(data, **json_kwargs).encode("utf-8"),
        )
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())

    def update(
        self,
        data: Dict[str, Any],
        token: Optional[Dict[str, Any]] = None,
        json_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if json_kwargs is None:
            json_kwargs = {}
        if token is None:
            token = self.fb.token
        request_ref = self.build_request_url()
        self.path = ""
        headers = self.build_headers(token)
        request_object = self.requests.patch(
            request_ref,
            headers=headers,
            data=json.dumps(data, **json_kwargs).encode("utf-8"),
        )
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())

    def remove(self, token: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if token is None:
            token = self.fb.token
        request_ref = self.build_request_url()
        self.path = ""
        headers = self.build_headers(token)
        request_object = self.requests.delete(request_ref, headers=headers)
        raise_detailed_error(request_object)
        return cast(Dict[str, Any], request_object.json())

    def stream(
        self,
        stream_handler: Any,
        token: Optional[Dict[str, Any]] = None,
        stream_id: Optional[str] = None,
    ) -> Stream:
        request_ref = self.build_request_url()
        return Stream(request_ref, stream_handler, self.build_headers, stream_id)

    def generate_key(self) -> str:
        push_chars = "-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz"
        now = int(time.time() * 1000)
        duplicate_time = now == self.last_push_time
        self.last_push_time = now
        time_stamp_chars: list[str] = [""] * 8
        for i in reversed(range(0, 8)):
            time_stamp_chars[i] = push_chars[now % 64]
            now = int(math.floor(now / 64))
        new_id = "".join(time_stamp_chars)
        if not duplicate_time:
            for i in range(0, 12):
                self.last_rand_chars.append(int(math.floor(uniform(0, 1) * 64)))
        else:
            for i in range(0, 11):
                if self.last_rand_chars[i] == 63:
                    self.last_rand_chars[i] = 0
                self.last_rand_chars[i] += 1
        for i in range(0, 12):
            new_id += push_chars[self.last_rand_chars[i]]
        return new_id
