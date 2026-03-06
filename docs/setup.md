# Setup Instructions

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (optional, for containerized deployment)

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/GIcsei/BAB.git
cd BAB
```

### 2. Install Dependencies

```bash
pip install uv
uv sync --frozen --group dev
```

### 3. Configure Environment

Copy the example environment file and customize:

```bash
cp truenas.env.example .env
```

Required environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_USER_DATA_DIR` | Directory for user data storage | `/var/app/user_data` |
| `APP_JOB_HOUR` | Scheduled job hour (0-23) | `18` |
| `APP_JOB_MINUTE` | Scheduled job minute (0-59) | `0` |
| `FIRESTORE_CREDENTIALS` | Path to Firebase service account JSON | — |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FILE` | Log file path (empty for stdout) | — |
| `LOG_JSON` | Enable JSON-formatted logs | `false` |
| `APP_ALLOW_UNSAFE_DESERIALIZE` | Allow pickle deserialization | `false` |
| `SELENIUM_DOWNLOADS_DIR` | Selenium download directory | — |
| `LOCAL_DOWNLOADS_DIR` | Local download directory | — |

### 4. Run the Application

```bash
# Development mode with auto-reload
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or use the dev script:

```bash
./scripts/dev.sh
```

### 5. Verify

```bash
curl http://localhost:8000/health
```

## Code Quality Tools

### Linting

```bash
uv run ruff check app tests
uv run black --check app tests
```

### Formatting

```bash
uv run black app tests
uv run ruff check --fix app tests
```

Or use the script:

```bash
./scripts/format.sh
```

### Type Checking

```bash
uv run mypy app
```

### Security Audit

```bash
uv run pip-audit
```
