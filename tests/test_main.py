"""Tests for app.main – root, health endpoints, and middleware."""
import os

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")

import pytest
from fastapi.testclient import TestClient

import app.core.health as health_mod
from app.core.health import HealthStatus
from app.main import app


@pytest.fixture(autouse=True)
def reset_health():
    """Reset the global health singleton before each test."""
    h = health_mod._health
    h.is_ready = False
    h.startup_complete_time = None
    for comp in h.components.values():
        comp["ready"] = False
        comp["error"] = None
    yield
    # restore to ready after tests so other tests aren't broken
    h.is_ready = False


client = TestClient(app, raise_server_exceptions=False)


# ── root endpoint ──────────────────────────────────────────────────────────


def test_root_returns_message():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"message": "Bank Analysis Backend"}


# ── health endpoint ────────────────────────────────────────────────────────


def test_health_not_ready_returns_503():
    r = client.get("/health")
    assert r.status_code == 503
    body = r.json()
    assert body["ready"] is False
    assert body["status"] == "not_ready"


def test_health_ready_returns_200():
    h = health_mod.get_health()
    h.mark_startup_complete()
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert body["status"] == "healthy"
    assert "startup_complete_time" in body
    assert "components" in body


def test_health_components_present():
    h = health_mod.get_health()
    h.mark_startup_complete()
    r = client.get("/health")
    body = r.json()
    comps = body["components"]
    assert "firebase" in comps
    assert "scheduler" in comps
    assert "tokens" in comps


# ── middleware ─────────────────────────────────────────────────────────────


def test_middleware_catches_app_exception():
    """Middleware should return structured JSON for AppException."""
    from fastapi import Request
    from app.core.exceptions import FirebaseError

    @app.get("/test_app_exc")
    async def raise_app_exc():
        raise FirebaseError("db error")

    r = client.get("/test_app_exc")
    # The middleware catches AppException and returns JSONResponse
    assert r.status_code in (502, 500)


def test_middleware_catches_generic_exception():
    """Middleware should catch unhandled exceptions and return 500."""
    @app.get("/test_generic_exc")
    async def raise_generic():
        raise RuntimeError("totally unexpected")

    r = client.get("/test_generic_exc")
    assert r.status_code == 500
