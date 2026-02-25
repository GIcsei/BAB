import os

import pytest

# Set environment variables at module level so they are available
# when test modules are imported during collection.
# credentials.py calls get_settings() at module level which caches
# the Settings singleton; these env vars must be set before that.
os.environ.setdefault("PYTEST_RUNNING", "1")
os.environ.setdefault("FIREBASE_API_KEY", "test-api-key")
os.environ.setdefault("APP_ALLOW_UNSAFE_DESERIALIZE", "true")


@pytest.fixture(autouse=True, scope="session")
def test_environment():
    yield
