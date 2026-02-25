import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def test_environment():
    os.environ.setdefault("PYTEST_RUNNING", "1")
    yield
