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
  }
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

List available pickle files for the authenticated user.

**Headers**: `Authorization: Bearer <idToken>`

**Response 200**:
```json
{
  "files": [
    {
      "filename": "report_2025.pkl",
      "size_bytes": 102400,
      "modified_ms": 1704067200000
    }
  ]
}
```

#### `GET /data/files/{filename}/preview`

Preview contents of a pickle file.

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

Extract x/y series for plotting.

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

## Error Response Format

All error responses follow this structure:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable description"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_TOKEN` | 401 | Token is invalid or expired |
| `TOKEN_EXPIRED` | 401 | Token has expired |
| `MISSING_TOKEN` | 401 | Authorization header missing |
| `LOGIN_FAILED` | 401 | Invalid credentials |
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
