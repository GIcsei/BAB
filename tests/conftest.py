import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def test_environment():
    os.environ.setdefault("PYTEST_RUNNING", "1")
    os.environ.setdefault("FIREBASE_API_KEY", "test-api-key")
    yield
