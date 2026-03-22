# API Documentation

## Base URL

```
http://<host>:<port>
```

Default port is `8000`.

## Authentication

All data endpoints require a Bearer token obtained via the login endpoint.

```
Authorization: Bearer <idToken>
```

## Endpoints

### Health

#### `GET /health`

Liveness and readiness probe.

**Response 200** (ready):
```json
{
  "status": "healthy",
  "ready": true,
  "startup_complete_time": "2025-01-01T12:00:00",
  "components": {
    "firebase": {"ready": true, "error": null},
    "scheduler": {"ready": true, "error": null},
    "tokens": {"ready": true, "error": null}
  },
  "version": "0.10.4",
  "uptime_seconds": 123.45
}
```

**Response 503** (not ready):
```json
{
  "status": "not_ready",
  "ready": false,
  "components": { ... }
}
```

#### `GET /`

Root endpoint. Returns application identity.

**Response 200**:
```json
{"message": "Bank Analysis Backend"}
```

---

### Authentication (`/user`)

#### `POST /user/login`

Authenticate a user with email and password.

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

**Response 200**:
```json
{
  "access_token": "<idToken>",
  "token_type": "bearer",
  "message": "Login successful"
}
```

**Response 401**: Invalid credentials.

#### `POST /user/logout`

Logout the authenticated user. Stops scheduled jobs and removes stored credentials.

**Headers**: `Authorization: Bearer <idToken>`

**Response 200**:
```json
true
```

#### `POST /user/password-reset`

Request a password reset email. No authentication required.

**Request Body**:
```json
{
  "email": "user@example.com"
}
```

**Response 200**:
```json
{
  "message": "If the email is registered, a password reset link has been sent."
}
```

> **Note**: This endpoint always returns a success message to prevent email enumeration attacks.

#### `PUT /user/collect_automatically`

Trigger an immediate data collection run for the authenticated user.

**Headers**: `Authorization: Bearer <idToken>`

**Response 200**:
```json
true
```

**Response 500**: Failed to start job.

#### `POST /user/next_run`

Get information about the next scheduled run.

**Headers**: `Authorization: Bearer <idToken>`

**Response 200**:
```json
{
  "seconds_until_next": 3600,
  "next_run_time": "2025-01-01T18:00:00"
}
```

**Response 404**: No scheduled job found.

#### `GET /user/job-status`

Get job status and deletion status for the authenticated user.

**Headers**: `Authorization: Bearer <idToken>`

**Response 200**:
```json
{
  "user_id": "abc123",
  "has_scheduled_job": true,
  "next_run": {
    "seconds_until_next_run": 3600,
    "next_run_timestamp_ms": 1704110400000
  },
  "deletion_pending": false
}
```

---

### NetBank Credentials (`/netbank`)

#### `POST /netbank/credentials`

Store encrypted NetBank credentials.

**Headers**: `Authorization: Bearer <idToken>`

**Request Body**:
```json
{
  "username": "netbank_user",
  "account_number": "12345678",
  "password": "netbank_password"
}
```

**Response 201**:
```json
{"status": "ok"}
```

#### `DELETE /netbank/credentials`

Remove stored credentials.

**Headers**: `Authorization: Bearer <idToken>`

**Response 204**: No content.
**Response 404**: Credentials not found.

---

### Data (`/data`)

#### `GET /data/list`

List available data files (pickle, CSV, Parquet) for the authenticated user.

**Headers**: `Authorization: Bearer <idToken>`

**Query Parameters**:
- `offset` (int, default: 0, min: 0): Pagination offset.
- `limit` (int, default: 50, range: 1-500): Maximum files per page.

**Response 200**:
```json
{
  "files": [
    {
      "filename": "report_2025.pkl",
      "size_bytes": 102400,
      "modified_ms": 1704067200000
    },
    {
      "filename": "data.csv",
      "size_bytes": 51200,
      "modified_ms": 1704153600000
    },
    {
      "filename": "summary.parquet",
      "size_bytes": 204800,
      "modified_ms": 1704240000000
    }
  ],
  "total_count": 3
}
```

#### `GET /data/files/{filename}/preview`

Preview contents of a data file. Supports `.pkl`, `.pickle`, `.csv`, and `.parquet` formats.

**Headers**: `Authorization: Bearer <idToken>`

**Query Parameters**:
- `rows` (int, default: 200, range: 1-5000): Maximum rows to return.

**Response 200** (DataFrame example):
```json
{
  "preview": {
    "type": "dataframe",
    "columns": [
      {"name": "date", "dtype": "datetime64[ns]"},
      {"name": "value", "dtype": "float64"}
    ],
    "rows": [{"date": "2025-01-01", "value": 42.0}],
    "n_rows": 1000
  }
}
```

**Response 400**: Invalid filename format.
**Response 403**: Deserialization disabled.
**Response 404**: File not found.
**Response 413**: File size exceeded.

#### `GET /data/files/{filename}/series`

Extract x/y series for plotting. Supports `.pkl`, `.pickle`, `.csv`, and `.parquet` formats.

**Headers**: `Authorization: Bearer <idToken>`

**Query Parameters**:
- `y` (string, required): Column name for Y-axis.
- `x` (string, optional): Column name for X-axis.
- `max_points` (int, default: 10000, range: 10-100000): Maximum data points.

**Response 200**:
```json
{
  "x": ["2025-01-01", "2025-01-02"],
  "y": [42.0, 43.5],
  "meta": {
    "y_column": "value",
    "n_points": 2
  }
}
```

---

### Admin (`/admin`)

#### `GET /admin/cleanup-metrics`

Return deletion worker metrics. No authentication required.

**Response 200**:
```json
{
  "last_run_at": "2025-01-01T12:00:00+00:00",
  "total_deleted": 5,
  "total_errors": 0,
  "total_scans": 42
}
```

**Response 503**: Deletion worker not available.

## Error Response Format

All error responses follow this structure:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description",
  "timestamp": "2025-01-01T12:00:00+00:00"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_TOKEN` | 401 | Token is invalid or expired |
| `TOKEN_EXPIRED` | 401 | Token has expired |
| `MISSING_TOKEN` | 401 | Authorization header missing |
| `LOGIN_FAILED` | 401 | Invalid credentials |
| `REGISTRATION_FAILED` | 400 | Registration failed |
| `USER_BLOCKED` | 403 | User account is blocked (pending deletion) |
| `FILE_NOT_FOUND` | 404 | Requested file does not exist |
| `FILE_SIZE_EXCEEDED` | 413 | File exceeds size limit |
| `DESERIALIZATION_ERROR` | 400 | Failed to deserialize file |
| `DESERIALIZATION_DISABLED` | 403 | Unsafe deserialization is disabled |
| `JOB_NOT_FOUND` | 404 | No scheduled job for user |
| `JOB_START_ERROR` | 500 | Failed to start scheduled job |
| `FIREBASE_ERROR` | 502 | Firebase operation failed |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

## OpenAPI Documentation

Interactive API documentation is available at:
- **Swagger UI**: `http://<host>:<port>/docs`
- **ReDoc**: `http://<host>:<port>/redoc`
