"""Tests for app.routers.netbank_credentials – store and delete credentials."""

import os

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth import get_current_user_id
from app.main import app


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user_id] = lambda: "netbank_user"
    yield
    app.dependency_overrides.pop(get_current_user_id, None)


client = TestClient(app, raise_server_exceptions=False)

CREDENTIALS_PAYLOAD = {
    "username": "myuser",
    "account_number": "ACC123",
    "password": "s3cr3t",
}


# ── POST /netbank/credentials ──────────────────────────────────────────────


def test_store_credentials_success():
    with patch("app.routers.netbank_credentials.save_user_credentials") as mock_save:
        mock_save.return_value = None
        r = client.post("/netbank/credentials", json=CREDENTIALS_PAYLOAD)
    assert r.status_code == 201
    assert r.json() == {"status": "ok"}
    mock_save.assert_called_once_with(
        user_id="netbank_user",
        username="myuser",
        account_number="ACC123",
        password="s3cr3t",
    )


def test_store_credentials_failure_returns_500():
    with patch(
        "app.routers.netbank_credentials.save_user_credentials",
        side_effect=RuntimeError("disk full"),
    ):
        r = client.post("/netbank/credentials", json=CREDENTIALS_PAYLOAD)
    assert r.status_code == 500


def test_store_credentials_missing_field_returns_422():
    r = client.post(
        "/netbank/credentials",
        json={"username": "u", "account_number": "A"},  # missing password
    )
    assert r.status_code == 422


# ── DELETE /netbank/credentials ────────────────────────────────────────────


def test_delete_credentials_success():
    with patch(
        "app.routers.netbank_credentials.delete_user_credentials", return_value=True
    ):
        r = client.delete("/netbank/credentials")
    assert r.status_code == 204


def test_delete_credentials_not_found_returns_404():
    with patch(
        "app.routers.netbank_credentials.delete_user_credentials", return_value=False
    ):
        r = client.delete("/netbank/credentials")
    assert r.status_code == 404
