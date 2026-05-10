import threading
import time
from collections import deque
from typing import Deque, Dict

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> int:
        now = time.monotonic()
        cutoff = now - float(window_seconds)

        with self._lock:
            events = self._events.setdefault(key, deque())
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= max_requests:
                retry_after = max(1, int(window_seconds - (now - events[0])))
                return retry_after

            events.append(now)
            return 0

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


_AUTH_ENDPOINT_LIMITER = InMemoryRateLimiter()


def _client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first = forwarded_for.split(",", maxsplit=1)[0].strip()
        if first:
            return first

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def enforce_auth_rate_limit(
    request: Request,
    endpoint_name: str,
    max_requests: int,
    window_seconds: int,
) -> None:
    key = f"{endpoint_name}:{_client_identifier(request)}"
    retry_after = _AUTH_ENDPOINT_LIMITER.check(
        key=key,
        max_requests=max_requests,
        window_seconds=window_seconds,
    )
    if retry_after > 0:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "RATE_LIMITED",
                "message": "Too many requests. Please try again later.",
            },
            headers={"Retry-After": str(retry_after)},
        )


def reset_auth_rate_limiter() -> None:
    _AUTH_ENDPOINT_LIMITER.reset()
