# Deployment Instructions

## Docker Deployment

### Build

```bash
docker build -t bab:latest -f docker/Dockerfile .
```

### Run (Development)

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
```

### Run (Production)

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d
```

### Run (TrueNAS)

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.truenas.yml up -d
```

## Production Startup Command

```bash
gunicorn -k uvicorn.workers.UvicornWorker -w 4 app.main:app --bind 0.0.0.0:8000
```

Or with uvicorn directly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Container Environment

### Required Volumes

| Mount Point | Description |
|------------|-------------|
| `/var/app/user_data` | Persistent user data directory |
| `/var/app/downloads` | Download staging directory |
| `/var/app/credentials.json` | Firebase service account (read-only) |

### Health Check

The container includes a built-in health check:

```
curl -fsS http://localhost:8000/health
```

- Interval: 30 seconds
- Timeout: 5 seconds
- Start period: 20 seconds
- Retries: 3

The `/health` endpoint returns:
- `200` when all components are ready
- `503` during startup or if components are unhealthy

### User Permissions

The container runs as `appuser` with configurable UID/GID:

| Variable | Description | Default |
|----------|-------------|---------|
| `PUID` | Process user ID | `568` (TrueNAS default) |
| `PGID` | Process group ID | `568` |

The entrypoint script dynamically remaps UID/GID for compatibility with host volume permissions.

## Multi-Worker Considerations

When running with multiple workers:

1. **Scheduler**: Only one worker acquires the file-based scheduler lock. Other workers skip scheduler initialization.
2. **Firebase Admin**: Each worker initializes its own Firebase Admin SDK instance.
3. **Token Registry**: Each worker maintains its own in-memory token registry, populated from disk on startup.
4. **File Locks**: The scheduler uses `fcntl.flock()` for process-safe file locking.

## Monitoring

### Logs

- Default: stdout (Docker-friendly)
- Optional file: Set `LOG_FILE=/var/app/app.log`
- JSON format: Set `LOG_JSON=true`
- Sensitive data (tokens, passwords) is automatically redacted

### Health Endpoint

Monitor component health via `GET /health`:

```json
{
  "status": "healthy",
  "ready": true,
  "startup_complete_time": "2025-01-01T12:00:00",
  "components": {
    "firebase": {"ready": true, "error": null},
    "scheduler": {"ready": true, "error": null},
    "tokens": {"ready": true, "error": null}
  }
}
```

## Security Notes

- Never commit Firebase service account credentials
- Use `NETBANK_MASTER_KEY` environment variable for credential encryption key
- All credential files are stored with restricted permissions (0o600)
- Pickle deserialization is disabled by default for security
