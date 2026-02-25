import json
import logging
import math
import time
from random import uniform

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote

from app.core.firestore_handler.DataDescriptor import Collection, Document
from app.core.firestore_handler.Query import FirestoreQueryBuilder
from app.core.firestore_handler.QueryHandler import Firebase
from app.core.firestore_handler.Utils import Stream, raise_detailed_error

logger = logging.getLogger(__name__)


class Database:
    """Database Service"""

    def __init__(self):
        fb = Firebase()
        self.fb = fb
        self.database_url = (
            "https://firestore.googleapis.com/v1/projects/"
            f"{fb.projectId}/databases/(default)/documents"
        )
        self.requests = fb.requests
        self.key = fb.api_key
        self.path = ""
        self.build_query = {}
        self.last_push_time = 0
        self.last_rand_chars = []
        # do not cache token here; read live from fb.token to avoid staleness
        # self.token = fb.token

    def order_by_key(self):
        self.build_query["orderBy"] = "$key"
        return self

    def order_by_value(self):
        self.build_query["orderBy"] = "$value"
        return self

    def order_by_field(self, order):
        self.build_query["orderBy"] = order
        return self

    def start_at(self, start):
        self.build_query["startAt"] = start
        return self

    def end_at(self, end):
        self.build_query["endAt"] = end
        return self

    def equal_to(self, equal):
        self.build_query["equalTo"] = equal
        return self

    def limit_to_first(self, limit_first):
        self.build_query["limitToFirst"] = limit_first
        return self

    def limit_to_last(self, limit_last):
        self.build_query["limitToLast"] = limit_last
        return self

    def listDocuments(self, token=None):
        if token is None:
            token = self.fb.token
        header = self.build_headers(token)
        url = self.build_request_url()
        response = self.requests.get(url=url, headers=header)
        raise_detailed_error(response)
        return response.json()

    def addStringQuery(self, query):
        self.build_query["StringQuery"] = query
        self.path = ":runQuery"
        return self

    def child(self, *args):
        new_path = "/".join([str(arg) for arg in args])
        if not self.path:
            self.path = ""
        self.path += "/{}".format(new_path)
        return self

    def build_request_url(self):
        parameters = {}
        for param in list(self.build_query):
            if type(self.build_query[param]) is str:
                parameters[param] = quote('"' + self.build_query[param] + '"')
            elif type(self.build_query[param]) is bool:
                parameters[param] = "true" if self.build_query[param] else "false"
            else:
                parameters[param] = self.build_query[param]
        # reset path and build_query for next query
        request_ref = "{0}{1}".format(self.database_url, self.path)
        return request_ref

    def build_headers(self, token=None):
        headers = {"content-type": "application/json; charset=UTF-8"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token['idToken']}"
        return headers

    def _request(self, token, json_kwargs={}):
        request_ref = self.build_request_url()
        # headers
        if token is None:
            token = self.fb.token
        headers = self.build_headers(token)
        # do request
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

    def filtering(self, response_dict: Collection, filters):
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

    def get(self, token=None, json_kwargs={}):
        if token is None:
            token = self.fb.token
        build_query = self.build_query
        query_key = self.path.split("/")[-1]

        request_dict = self._request(token)

        response_dict = None
        if len(request_dict) == 1 and isinstance(request_dict, list):
            request_dict["documents"] = request_dict
        if len(request_dict) == 1 and request_dict.get("documents"):
            response_dict = Collection.from_list(query_key, request_dict["documents"])
        if not isinstance(response_dict, Collection):
            response_dict = Collection(query_key)
            response_dict.add_doc(Document.from_dict(request_dict))

        if response_dict is None:
            raise ValueError(
                "No answer had been received, document cannot be created on: "
                f"{request_dict}!"
            )

        if build_query:
            response_dict = self.filtering(response_dict, build_query)

        return response_dict

    def push(self, data, token=None, json_kwargs={}):
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
        return request_object.json()

    def set(self, data, token=None, json_kwargs={}):
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
        return request_object.json()

    def update(self, data, token=None, json_kwargs={}):
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
        return request_object.json()

    def remove(self, token=None):
        if token is None:
            token = self.fb.token
        request_ref = self.build_request_url()
        self.path = ""
        headers = self.build_headers(token)
        request_object = self.requests.delete(request_ref, headers=headers)
        raise_detailed_error(request_object)
        return request_object.json()

    # TODO
    def stream(self, stream_handler, token=None, stream_id=None):
        request_ref = self.build_request_url(token)
        return Stream(request_ref, stream_handler, self.build_headers, stream_id)

    def generate_key(self):
        push_chars = "-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz"
        now = int(time.time() * 1000)
        duplicate_time = now == self.last_push_time
        self.last_push_time = now
        time_stamp_chars = [0] * 8
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
