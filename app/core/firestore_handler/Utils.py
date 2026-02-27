import json
import re
import socket
import threading
import time
from random import uniform
from typing import Any, Callable, Dict, Optional

from requests import Response, Session
from requests.exceptions import HTTPError
from sseclient import SSEClient


def parse_to_firestore(value: str) -> Dict[str, Any]:
    value = value.strip()

    if value.lower() == "true":
        return {"booleanValue": True}
    elif value.lower() == "false":
        return {"booleanValue": False}

    if re.match(r"^-?\d+(\.\d+)?$", value):
        if "." in value:
            return {"doubleValue": float(value)}
        else:
            return {"integerValue": value}

    if re.match(r"^['\"].*['\"]$", value):
        return {"stringValue": value.strip("'\"")}

    return {"stringValue": value}


def raise_detailed_error(request_object: Response) -> None:
    try:
        request_object.raise_for_status()
    except HTTPError as e:
        raise HTTPError(e, request_object.text)


class KeepAuthSession(Session):
    """
    A session that doesn't drop Authentication on redirects between domains.
    """

    def rebuild_auth(self, prepared_request: Any, response: Response) -> None:
        return None


class ClosableSSEClient(SSEClient):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.should_connect = True
        super().__init__(*args, **kwargs)

    def _connect(self) -> None:
        if self.should_connect:
            super()._connect()
        else:
            raise StopIteration()

    def close(self) -> None:
        self.should_connect = False
        self.retry = 0
        self.resp.raw._fp.fp.raw._sock.shutdown(socket.SHUT_RDWR)
        self.resp.raw._fp.fp.raw._sock.close()


class Stream:
    def __init__(
        self,
        url: str,
        stream_handler: Callable[[Dict[str, Any]], None],
        build_headers: Callable[..., Dict[str, str]],
        stream_id: Optional[str],
    ) -> None:
        self.build_headers = build_headers
        self.url = url
        self.stream_handler = stream_handler
        self.stream_id = stream_id
        self.sse: Optional[ClosableSSEClient] = None
        self.thread: Optional[threading.Thread] = None
        self.start()

    def make_session(self) -> Session:
        session = KeepAuthSession()
        return session

    def start(self) -> "Stream":
        self.thread = threading.Thread(target=self.start_stream)
        self.thread.start()
        return self

    def start_stream(self) -> None:
        self.sse = ClosableSSEClient(
            self.url, session=self.make_session(), build_headers=self.build_headers
        )
        sse = self.sse
        if sse is None:
            return
        for msg in sse:
            if msg:
                msg_data = json.loads(msg.data)
                msg_data["event"] = msg.event
                if self.stream_id:
                    msg_data["stream_id"] = self.stream_id
                self.stream_handler(msg_data)

    def close(self) -> "Stream":
        sse = self.sse
        if sse is None:
            return self
        while not hasattr(sse, "resp"):
            time.sleep(0.001)
        sse.running = False
        sse.close()
        if self.thread:
            self.thread.join()
        return self


class DocumentKeyGenerator:
    PUSH_CHARS = "-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz"

    def __init__(self) -> None:
        self.last_push_time = 0
        self.last_rand_chars: list[int] = [0] * 12

    def generate_key(self) -> str:
        now = int(time.time() * 1000)
        duplicate_time = now == self.last_push_time
        self.last_push_time = now

        time_stamp_chars: list[str] = [""] * 8
        for i in reversed(range(8)):
            time_stamp_chars[i] = self.PUSH_CHARS[now % 64]
            now //= 64

        new_id = "".join(time_stamp_chars)

        if not duplicate_time:
            self.last_rand_chars = [int(uniform(0, 64)) for _ in range(12)]
        else:
            for i in range(11):
                if self.last_rand_chars[i] == 63:
                    self.last_rand_chars[i] = 0
                self.last_rand_chars[i] += 1

        new_id += "".join(self.PUSH_CHARS[i] for i in self.last_rand_chars)
        return new_id
