"""Functional-test conftest — provides auth override so admin endpoints are accessible."""
import pytest
from app.core.auth import get_current_user_id
from app.main import app


@pytest.fixture(autouse=True)
def _ensure_admin_auth_override():
    """Provide a default auth override for admin endpoints in functional tests."""
    app.dependency_overrides.setdefault(get_current_user_id, lambda: "test_admin")
    yield
