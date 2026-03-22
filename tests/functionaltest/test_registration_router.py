"""Functional tests for POST /user/register and POST /user/unregister endpoints."""

import os

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

from unittest.mock import MagicMock, patch

import pytest
from app.core.auth import get_current_user_id, get_firebase_dep
from app.main import app
from app.routers.login import get_scheduler_dep
from fastapi.testclient import TestClient

# ── fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def override_deps():
    """Override infrastructure deps so router tests run without real Firebase."""
    mock_scheduler = MagicMock()
    mock_firebase = MagicMock()
    app.dependency_overrides[get_current_user_id] = lambda: "test_user"
    app.dependency_overrides[get_scheduler_dep] = lambda: mock_scheduler
    app.dependency_overrides[get_firebase_dep] = lambda: mock_firebase
    yield mock_scheduler, mock_firebase
    app.dependency_overrides.pop(get_current_user_id, None)
    app.dependency_overrides.pop(get_scheduler_dep, None)
    app.dependency_overrides.pop(get_firebase_dep, None)


client = TestClient(app, raise_server_exceptions=False)


# ── POST /user/register ────────────────────────────────────────────────────


def test_register_success():
    from app.schemas.login import RegisterResponse

    mock_resp = RegisterResponse(
        access_token="tok123",
        user_id="uid_abc",
        message="Registration successful",
    )

    with patch("app.routers.login.register_user", return_value=mock_resp):
        r = client.post(
            "/user/register",
            json={"email": "new@example.com", "password": "secret123"},
        )

    assert r.status_code == 201
    data = r.json()
    assert data["access_token"] == "tok123"
    assert data["user_id"] == "uid_abc"
    assert data["message"] == "Registration successful"
    assert data["token_type"] == "bearer"


def test_register_invalid_email_returns_422():
    r = client.post(
        "/user/register",
        json={"email": "not-an-email", "password": "pw"},
    )
    assert r.status_code == 422


def test_register_missing_password_returns_422():
    r = client.post(
        "/user/register",
        json={"email": "user@example.com"},
    )
    assert r.status_code == 422


def test_register_failure_registration_failed_error_returns_400():
    from app.core.exceptions import RegistrationFailedError

    with patch(
        "app.routers.login.register_user",
        side_effect=RegistrationFailedError("email already in use"),
    ):
        r = client.post(
            "/user/register",
            json={"email": "dup@example.com", "password": "pw"},
        )
    assert r.status_code == 400
    assert r.json()["detail"]["error"] == "REGISTRATION_FAILED"


def test_register_unexpected_exception_returns_400():
    with patch(
        "app.routers.login.register_user",
        side_effect=RuntimeError("unexpected"),
    ):
        r = client.post(
            "/user/register",
            json={"email": "crash@example.com", "password": "pw"},
        )
    assert r.status_code == 400


# ── POST /user/unregister ──────────────────────────────────────────────────


def test_unregister_success():
    import time

    from app.schemas.login import UnregisterResponse

    now_ms = int(time.time() * 1000)
    mock_resp = UnregisterResponse(
        message="User unregistered. Account and data will be permanently deleted in 60 days.",
        deletion_scheduled_at_ms=now_ms,
        deletion_at_ms=now_ms + 60 * 24 * 60 * 60 * 1000,
    )

    with patch("app.routers.login.unregister_user", return_value=mock_resp):
        r = client.post("/user/unregister")

    assert r.status_code == 200
    data = r.json()
    assert "unregistered" in data["message"]
    assert data["deletion_at_ms"] > data["deletion_scheduled_at_ms"]


def test_unregister_generic_exception_returns_500():
    with patch(
        "app.routers.login.unregister_user",
        side_effect=RuntimeError("something broke"),
    ):
        r = client.post("/user/unregister")
    assert r.status_code in (500, 502)


def test_unregister_requires_auth():
    """Without the auth override, /user/unregister should require a token."""
    app.dependency_overrides.pop(get_current_user_id, None)
    try:
        r = client.post("/user/unregister")
        # Without a valid Bearer token the auth layer returns 403
        assert r.status_code in (401, 403)
    finally:
        app.dependency_overrides[get_current_user_id] = lambda: "test_user"
