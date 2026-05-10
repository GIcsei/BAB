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
gunicorn -k uvicorn.workers.UvicornWorker -w 1 app.main:app --bind 0.0.0.0:8000
```

Or with uvicorn directly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
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
- `503` only during startup before readiness is marked complete
- `200` after startup, with per-component readiness in `components` (including `selenium`)

### User Permissions

The container runs as `appuser` with configurable UID/GID:

| Variable | Description | Default |
|----------|-------------|---------|
| `PUID` | Process user ID | `568` (TrueNAS default) |
| `PGID` | Process group ID | `568` |

The entrypoint script dynamically remaps UID/GID for compatibility with host volume permissions.

## Worker Model

Runtime is pinned to one worker (`--workers 1`) in image and compose runtime commands for consistency of in-memory auth/token state across requests.

## Monitoring

### Logs

- Default: stdout (Docker-friendly)
- Optional file: Set `LOG_FILE=/var/app/app.log`
- JSON format: Set `LOG_JSON=true`
- Rotation: `LOG_ROTATION_MAX_BYTES` (default `10485760`) and `LOG_ROTATION_BACKUP_COUNT` (default `5`)
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
    "tokens": {"ready": true, "error": null},
    "selenium": {"ready": true, "error": null}
  }
}
```

## Security Notes

- Never commit Firebase service account credentials
- Use `NETBANK_MASTER_KEY` environment variable for credential encryption key
- All credential files are stored with restricted permissions (0o600)
- Pickle deserialization is disabled by default for security
