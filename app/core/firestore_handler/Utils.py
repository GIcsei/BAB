from random import uniform
import re
from typing import Any, Dict
from requests import Session
from requests.exceptions import HTTPError

import json
import time
from sseclient import SSEClient
import threading
import socket


def parse_to_firestore(value: str) -> Dict[str, Any]:
    value = value.strip()

    if value.lower() == "true":
        return {"booleanValue": True}
    elif value.lower() == "false":
        return {"booleanValue": False}

    if re.match(r"^-?\d+(\.\d+)?$", value):
        if '.' in value:
            return {"doubleValue": float(value)}
        else:
            return {"integerValue": value}

    if re.match(r"^['\"].*['\"]$", value):
        return {"stringValue": value.strip('\'"')}

    return {"stringValue": value}

def raise_detailed_error(request_object):
    try:
        request_object.raise_for_status()
    except HTTPError as e:
        # raise detailed error message
        # TODO: Check if we get a { "error" : "Permission denied." } and handle automatically
        raise HTTPError(e, request_object.text)

class KeepAuthSession(Session):
    """
    A session that doesn't drop Authentication on redirects between domains.
    """

    def rebuild_auth(self, prepared_request, response):
        pass


class ClosableSSEClient(SSEClient):
    def __init__(self, *args, **kwargs):
        self.should_connect = True
        super(ClosableSSEClient, self).__init__(*args, **kwargs)

    def _connect(self):
        if self.should_connect:
            super(ClosableSSEClient, self)._connect()
        else:
            raise StopIteration()

    def close(self):
        self.should_connect = False
        self.retry = 0
        self.resp.raw._fp.fp.raw._sock.shutdown(socket.SHUT_RDWR)
        self.resp.raw._fp.fp.raw._sock.close()

class Stream:
    def __init__(self, url, stream_handler, build_headers, stream_id):
        self.build_headers = build_headers
        self.url = url
        self.stream_handler = stream_handler
        self.stream_id = stream_id
        self.sse = None
        self.thread = None
        self.start()

    def make_session(self):
        """
        Return a custom session object to be passed to the ClosableSSEClient.
        """
        session = KeepAuthSession()
        return session

    def start(self):
        self.thread = threading.Thread(target=self.start_stream)
        self.thread.start()
        return self

    def start_stream(self):
        self.sse = ClosableSSEClient(self.url, session=self.make_session(), build_headers=self.build_headers)
        for msg in self.sse:
            if msg:
                msg_data = json.loads(msg.data)
                msg_data["event"] = msg.event
                if self.stream_id:
                    msg_data["stream_id"] = self.stream_id
                self.stream_handler(msg_data)

    def close(self):
        while not self.sse and not hasattr(self.sse, 'resp'):
            time.sleep(0.001)
        self.sse.running = False
        self.sse.close()
        self.thread.join()
        return self

class DocumentKeyGenerator:
    PUSH_CHARS = '-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz'

    def __init__(self):
        self.last_push_time = 0
        self.last_rand_chars = [0] * 12

    def generate_key(self):
        now = int(time.time() * 1000)
        duplicate_time = now == self.last_push_time
        self.last_push_time = now

        time_stamp_chars = [0] * 8
        for i in reversed(range(8)):
            time_stamp_chars[i] = self.PUSH_CHARS[now % 64]
            now //= 64

        new_id = ''.join(time_stamp_chars)

        if not duplicate_time:
            self.last_rand_chars = [int(uniform(0, 64)) for _ in range(12)]
        else:
            for i in range(11):
                if self.last_rand_chars[i] == 63:
                    self.last_rand_chars[i] = 0
                self.last_rand_chars[i] += 1

        new_id += ''.join(self.PUSH_CHARS[i] for i in self.last_rand_chars)
        return new_id