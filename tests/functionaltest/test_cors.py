"""Tests for CORS middleware configuration."""

import os

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app, raise_server_exceptions=False)


def test_cors_headers_present_on_allowed_origin():
    r = client.options(
        "/",
        headers={
            "Origin": "http://localhost:5000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" in r.headers


def test_cors_wildcard_allows_any_origin():
    r = client.get("/", headers={"Origin": "http://example.com"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") in ("*", "http://example.com")


def test_cors_preflight_returns_allowed_methods():
    r = client.options(
        "/user/login",
        headers={
            "Origin": "http://localhost:5000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code in (200, 204)
    allow_methods = r.headers.get("access-control-allow-methods", "")
    assert allow_methods != ""
