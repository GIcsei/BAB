"""Tests for app.routers.login – login/logout/trigger/next_run routes."""

import os

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

from unittest.mock import MagicMock, patch

import pytest
from app.core.auth import get_current_user_id, get_firebase_dep
from app.main import app
from app.routers.login import get_scheduler_dep
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def override_auth():
    """Override auth and infrastructure deps so router tests don't need real Firebase."""
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


# ── POST /user/login ───────────────────────────────────────────────────────


def test_login_success():
    mock_resp = MagicMock()
    mock_resp.access_token = "tok123"
    mock_resp.token_type = "bearer"
    mock_resp.message = "Login successful"

    with patch("app.routers.login.login_user", return_value=mock_resp):
        r = client.post(
            "/user/login",
            json={"email": "user@example.com", "password": "password"},
        )
    assert r.status_code == 200


def test_login_failure_returns_401():
    with patch(
        "app.routers.login.login_user",
        side_effect=ValueError("bad credentials"),
    ):
        r = client.post(
            "/user/login",
            json={"email": "bad@example.com", "password": "wrong"},
        )
    assert r.status_code == 401


def test_login_failure_with_login_failed_error_returns_401():
    """LoginFailedError specifically triggers the first except branch (lines 25-26)."""
    from app.core.exceptions import LoginFailedError

    with patch(
        "app.routers.login.login_user",
        side_effect=LoginFailedError("invalid creds"),
    ):
        r = client.post(
            "/user/login",
            json={"email": "fail@example.com", "password": "bad"},
        )
    assert r.status_code == 401


def test_login_invalid_email_returns_422():
    r = client.post(
        "/user/login",
        json={"email": "not-an-email", "password": "pw"},
    )
    assert r.status_code == 422


# ── POST /user/logout ──────────────────────────────────────────────────────


def test_logout_success():
    with patch("app.routers.login.logout_user", return_value=True):
        r = client.post("/user/logout")
    assert r.status_code == 200
    assert r.json() is True


def test_logout_failure():
    with patch(
        "app.routers.login.logout_user",
        side_effect=RuntimeError("logout error"),
    ):
        r = client.post("/user/logout")
    assert r.status_code in (500, 502)


# ── PUT /user/collect_automatically ───────────────────────────────────────


def test_trigger_run_success(override_auth):
    mock_scheduler, _ = override_auth
    mock_scheduler.trigger_run_for_user.return_value = True
    r = client.put("/user/collect_automatically")
    assert r.status_code == 200
    assert r.json() is True


def test_trigger_run_returns_false_raises_500(override_auth):
    mock_scheduler, _ = override_auth
    mock_scheduler.trigger_run_for_user.return_value = False
    r = client.put("/user/collect_automatically")
    assert r.status_code in (500, 502)


def test_trigger_run_exception(override_auth):
    mock_scheduler, _ = override_auth
    mock_scheduler.trigger_run_for_user.side_effect = RuntimeError("boom")
    r = client.put("/user/collect_automatically")
    assert r.status_code in (500, 502)


# ── POST /user/next_run ────────────────────────────────────────────────────


def test_next_run_returns_info(override_auth):
    mock_scheduler, _ = override_auth
    mock_scheduler.get_next_run_for_user.return_value = {
        "seconds_until_next_run": 3600,
        "next_run_timestamp_ms": 9999999999,
    }
    r = client.post("/user/next_run")
    assert r.status_code == 200
    data = r.json()
    assert data["seconds_until_next_run"] == 3600


def test_next_run_no_job_returns_404(override_auth):
    mock_scheduler, _ = override_auth
    mock_scheduler.get_next_run_for_user.return_value = None
    r = client.post("/user/next_run")
    assert r.status_code == 404


def test_next_run_generic_exception_returns_500(override_auth):
    """Generic exception in next_run triggers lines 79-81."""
    mock_scheduler, _ = override_auth
    mock_scheduler.get_next_run_for_user.side_effect = RuntimeError("scheduler down")
    r = client.post("/user/next_run")
    assert r.status_code in (500, 502)

# ── GET /user/me ───────────────────────────────────────────────────────────


def test_me_returns_user_id():
    r = client.get("/user/me")
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == "test_user"


# ── GET /user/next_run ─────────────────────────────────────────────────────


def test_get_next_run_returns_info(override_auth):
    mock_scheduler, _ = override_auth
    mock_scheduler.get_next_run_for_user.return_value = {
        "seconds_until_next_run": 1800,
        "next_run_timestamp_ms": 8888888888,
    }
    r = client.get("/user/next_run")
    assert r.status_code == 200
    data = r.json()
    assert data["seconds_until_next_run"] == 1800


def test_get_next_run_no_job_returns_404(override_auth):
    mock_scheduler, _ = override_auth
    mock_scheduler.get_next_run_for_user.return_value = None
    r = client.get("/user/next_run")
    assert r.status_code == 404
