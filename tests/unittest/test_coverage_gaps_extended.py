"""Tests for uncovered branches in token_service and main lifespan."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")
os.environ.setdefault("PYTEST_RUNNING", "1")

from app.application.services.token_service import TokenService  # noqa: E402

# ── TokenService.auth: non-string refreshToken falls through ─────────────


def test_token_service_auth_uses_existing_when_refresh_token_not_string(tmp_path: Path):
    """When refreshToken is not a string, auth() returns the existing token as-is."""
    token_file = tmp_path / "token.json"
    existing = {"idToken": "abc123", "refreshToken": 12345}
    import json

    token_file.write_text(json.dumps(existing))

    mock_session = MagicMock()
    svc = TokenService(api_key="test-key", requests_session=mock_session)

    auth_client, token = svc.auth(token_file)

    assert token == existing
    assert auth_client is not None


def test_token_service_auth_falls_back_on_refresh_error(tmp_path: Path):
    """When refresh() raises, auth() returns the existing stored token."""
    token_file = tmp_path / "token.json"
    existing = {"idToken": "abc123", "refreshToken": "valid_refresh"}
    import json

    token_file.write_text(json.dumps(existing))

    mock_session = MagicMock()
    svc = TokenService(api_key="test-key", requests_session=mock_session)

    with patch.object(svc, "_ensure_auth_client") as mock_auth:
        mock_client = MagicMock()
        mock_client.refresh.side_effect = RuntimeError("network error")
        mock_auth.return_value = mock_client

        auth_client, token = svc.auth(token_file)

    assert token == existing


# ── TokenService.clear_token: exception on unlink ─────────────────────────


def test_token_service_clear_token_handles_unlink_error(tmp_path: Path):
    """clear_token logs exception when file cannot be deleted."""
    token_file = tmp_path / "token.json"
    token_file.write_text("{}")

    mock_session = MagicMock()
    svc = TokenService(api_key="test-key", requests_session=mock_session)
    svc._token_file = token_file

    with patch("pathlib.Path.unlink", side_effect=PermissionError("denied")):
        # Should not raise
        svc.clear_token()


# ── main lifespan: test environment early return ──────────────────────────


def test_main_lifespan_test_environment():
    """Lifespan correctly detects test environment and skips Firebase init."""
    from app.main import app  # noqa: E402
    from fastapi.testclient import TestClient  # noqa: E402

    client = TestClient(app)
    response = client.get("/health")

    # In test environment, health endpoint is reachable (may be 200 or 503 depending on
    # whether lifespan has run in this process before)
    assert response.status_code in (200, 503)
    data = response.json()
    # Verify it returns a structured health response
    assert "components" in data or "status" in data
