# Testing Instructions

## Running Tests

### Full Test Suite

```bash
uv run pytest -v
```

### With Coverage

```bash
uv run pytest -v --cov=app --cov-report=term-missing --cov-report=html:htmlcov
```

### Run Specific Test Category

```bash
# Unit tests only
uv run pytest tests/unittest/ -v

# Integration tests only
uv run pytest tests/integrationtest/ -v

# Functional tests only
uv run pytest tests/functionaltest/ -v
```

## Test Structure

Tests are organized into three categories:

```
tests/
├── conftest.py            # Shared fixtures and test environment setup
├── unittest/              # Isolated unit tests with mocked dependencies
├── integrationtest/       # Tests verifying service + repository interaction
└── functionaltest/        # End-to-end API tests using FastAPI TestClient
```

### Unit Tests (`tests/unittest/`)

Test isolated logic with mocked external dependencies.

- Mock infrastructure boundaries (Firebase, file system, HTTP)
- Test individual functions and classes
- Fast execution, no external service requirements

### Integration Tests (`tests/integrationtest/`)

Test service + repository interaction.

- Verify interaction between services, handlers, and adapters
- May use temporary databases or file systems
- Test data flow across module boundaries

### Functional Tests (`tests/functionaltest/`)

Test full API endpoints through FastAPI TestClient.

- Exercise HTTP request/response cycle
- Verify status codes, response bodies, and error handling
- Test authentication flow end-to-end

## Test Configuration

### Environment Variables

Tests automatically set the following environment variables (via `conftest.py`):

- `PYTEST_RUNNING=1`: Enables test mode, skips Firebase initialization
- `FIREBASE_API_KEY=test-api-key`: Provides a mock API key
- `APP_ALLOW_UNSAFE_DESERIALIZE=true`: Allows pickle deserialization in tests

### Coverage Configuration

Coverage settings are defined in `pyproject.toml`:

```toml
[tool.coverage.run]
branch = true
source = ["app"]
omit = ["tests/*"]

[tool.coverage.report]
show_missing = true
skip_covered = true
```

## Writing New Tests

### Guidelines

1. **Maintain existing coverage** — do not remove or weaken existing tests
2. **Update tests if logic changes** — keep tests in sync with code
3. **Ensure deterministic behavior** — avoid reliance on timing or ordering
4. **Mock infrastructure boundaries only** — do not mock business logic
5. **Add tests for new edge cases** — when introducing changes

### Example Unit Test

```python
from unittest.mock import MagicMock
from app.services.data_service import list_pickles_for_user
from pathlib import Path

def test_list_pickles_empty_dir(tmp_path: Path):
    result = list_pickles_for_user(tmp_path, "nonexistent_user")
    assert result == []
```

### Example Functional Test

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code in (200, 503)
```
