"""Deep Utils coverage tests for SSE/Stream classes."""

import socket
import threading
from unittest.mock import MagicMock, patch

import pytest

from app.core.firestore_handler.Utils import ClosableSSEClient, Stream

# ── ClosableSSEClient._connect with should_connect=False (line 61) ────────


def test_closable_sse_client_connect_raises_stop_when_disabled():
    """_connect raises StopIteration when should_connect is False."""
    client = ClosableSSEClient.__new__(ClosableSSEClient)
    client.should_connect = False

    with pytest.raises(StopIteration):
        client._connect()


# ── ClosableSSEClient.close – socket operations (lines 63-67) ────────────


def test_closable_sse_client_close_sets_flags():
    """ClosableSSEClient.close disables reconnection and closes socket."""
    client = ClosableSSEClient.__new__(ClosableSSEClient)
    client.should_connect = True
    client.retry = 3

    # Set up mock response chain
    mock_sock = MagicMock()
    mock_fp_inner = MagicMock()
    mock_fp_inner._sock = mock_sock
    mock_fp_outer = MagicMock()
    mock_fp_outer.fp = MagicMock()
    mock_fp_outer.fp.raw = mock_fp_inner
    mock_raw = MagicMock()
    mock_raw._fp = mock_fp_outer

    mock_resp = MagicMock()
    mock_resp.raw = mock_raw
    client.resp = mock_resp

    client.close()

    assert client.should_connect is False
    assert client.retry == 0
    mock_sock.shutdown.assert_called_once_with(socket.SHUT_RDWR)
    mock_sock.close.assert_called_once()


# ── Stream.__init__ and start (lines 72-78, 88-90) ────────────────────────


def test_stream_init_and_start(monkeypatch):
    """Stream.__init__ creates a thread and starts it."""
    mock_sse = MagicMock()
    mock_sse.__iter__ = MagicMock(return_value=iter([]))  # no events

    with patch(
        "app.core.firestore_handler.Utils.ClosableSSEClient", return_value=mock_sse
    ):
        s = Stream(
            url="http://example.com/stream",
            stream_handler=lambda data: None,
            build_headers=lambda: {},
            stream_id="sid1",
        )

    # Wait for thread to finish
    s.thread.join(timeout=1.0)
    assert not s.thread.is_alive()


# ── Stream.start_stream – processes messages (lines 93-102) ──────────────


def test_stream_start_stream_processes_messages():
    """Stream.start_stream calls stream_handler for each message."""
    import json

    received = []

    def handler(data):
        received.append(data)

    # Create a mock SSE message
    mock_msg = MagicMock()
    mock_msg.data = json.dumps({"key": "value"})
    mock_msg.event = "test_event"

    # Falsy message (should be skipped)
    null_msg = None

    mock_sse = MagicMock()
    mock_sse.__iter__ = MagicMock(return_value=iter([null_msg, mock_msg]))

    with patch(
        "app.core.firestore_handler.Utils.ClosableSSEClient", return_value=mock_sse
    ):
        s = Stream(
            url="http://example.com/stream",
            stream_handler=handler,
            build_headers=lambda: {},
            stream_id=None,
        )

    s.thread.join(timeout=1.0)
    assert len(received) == 1
    assert received[0]["key"] == "value"
    assert received[0]["event"] == "test_event"


def test_stream_start_stream_with_stream_id():
    """Stream.start_stream adds stream_id to message data when set."""
    import json

    received = []

    mock_msg = MagicMock()
    mock_msg.data = json.dumps({"x": 1})
    mock_msg.event = "ev"

    mock_sse = MagicMock()
    mock_sse.__iter__ = MagicMock(return_value=iter([mock_msg]))

    with patch(
        "app.core.firestore_handler.Utils.ClosableSSEClient", return_value=mock_sse
    ):
        s = Stream(
            url="http://example.com/stream",
            stream_handler=lambda d: received.append(d),
            build_headers=lambda: {},
            stream_id="my_stream_id",
        )

    s.thread.join(timeout=1.0)
    assert received[0]["stream_id"] == "my_stream_id"


# ── Stream.close (lines 104-110) ──────────────────────────────────────────


def test_stream_close():
    """Stream.close waits for SSE, then closes and joins thread."""
    mock_sse = MagicMock()
    mock_sse.__iter__ = MagicMock(return_value=iter([]))
    mock_sse.resp = MagicMock()  # has resp attribute

    with patch(
        "app.core.firestore_handler.Utils.ClosableSSEClient", return_value=mock_sse
    ):
        s = Stream(
            url="http://example.com/stream",
            stream_handler=lambda d: None,
            build_headers=lambda: {},
            stream_id=None,
        )

    s.thread.join(timeout=1.0)
    # Now manually set sse so close doesn't hang
    s.sse = mock_sse

    result = s.close()
    assert result is s
    mock_sse.close.assert_called_once()


def test_stream_close_waits_for_sse_init():
    """Stream.close waits (line 106) while sse is None, then closes when set."""
    mock_sse = MagicMock()
    mock_sse.resp = MagicMock()

    # Create stream manually without starting thread
    s = Stream.__new__(Stream)
    s.sse = None
    s.stream_handler = lambda d: None
    s.stream_id = None
    s.build_headers = lambda: {}
    s.url = "http://example.com"
    s.thread = MagicMock()
    s.thread.join = MagicMock()

    def set_sse_after_delay():
        import time

        time.sleep(0.01)  # short delay
        s.sse = mock_sse

    t = threading.Thread(target=set_sse_after_delay, daemon=True)
    t.start()

    # close() should loop (line 106) until sse is set
    result = s.close()
    assert result is s
    mock_sse.close.assert_called_once()
