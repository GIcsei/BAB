# Architecture Overview

## System Design

BAB (Bank Analysis Backend) is a FastAPI-based backend service designed for authenticated data ingestion, processing, and visualization. It runs in a containerized environment (Docker/TrueNAS) with multi-worker support.

## Layer Architecture

```
┌─────────────────────────────────────────┐
│            FastAPI Routers              │  ← HTTP transport layer
│         (app/routers/)                  │
├─────────────────────────────────────────┤
│            Services                     │  ← Business logic
│         (app/services/)                 │
├─────────────────────────────────────────┤
│         Application Services            │  ← Token lifecycle, orchestration
│       (app/application/services/)       │
├─────────────────────────────────────────┤
│              Core                       │  ← Domain models, auth, config
│           (app/core/)                   │
├─────────────────────────────────────────┤
│          Infrastructure                 │  ← Firebase, scheduler adapters
│       (app/infrastructure/)             │
└─────────────────────────────────────────┘
```

## Directory Structure

```
app/
├── main.py                      # FastAPI entrypoint, lifespan, middleware
├── routers/                     # HTTP route handlers (thin controllers)
│   ├── login.py                 # Auth endpoints (login/logout/trigger/next_run)
│   ├── netbank_credentials.py   # NetBank credential management
│   └── data_plot.py             # Data listing, preview, series extraction
├── schemas/                     # Pydantic request/response models
│   └── login.py                 # LoginRequest, LoginResponse
├── services/                    # Business logic layer
│   ├── login_service.py         # Login/logout orchestration
│   ├── data_service.py          # File loading, pickle deserialization, series extraction
│   └── scheduler.py             # Scheduler service wrapper
├── core/                        # Core domain and utilities
│   ├── config.py                # Environment-based configuration (Settings)
│   ├── auth.py                  # FastAPI auth dependencies
│   ├── exceptions.py            # Typed exception hierarchy
│   ├── error_mapping.py         # Exception → HTTP response mapping
│   ├── health.py                # Health check tracker
│   ├── logging_config.py        # Structured logging with token redaction
│   ├── firebase_init.py         # Firebase Admin SDK initialization
│   ├── firestore_handler/       # Firestore persistence layer
│   │   ├── QueryHandler.py      # Firebase singleton, session management
│   │   ├── DatabaseHandler.py   # Firestore REST client with retry logic
│   │   ├── FirestoreService.py  # High-level CRUD operations
│   │   ├── DataDescriptor.py    # Document/Collection models
│   │   ├── Query.py             # Firestore query builder
│   │   ├── User.py              # Auth token model
│   │   ├── Utils.py             # Validation, path handling
│   │   └── Config.py            # Firestore constants
│   └── netbank/                 # NetBank integration
│       ├── credentials.py       # Fernet-encrypted credential storage
│       ├── getReport.py         # Selenium-based report downloader
│       └── utils.py             # Report formatting utilities
├── application/
│   └── services/
│       └── token_service.py     # Token persistence, registry, refresh
└── infrastructure/
    ├── firebase/
    │   ├── auth.py              # Firebase auth adapter
    │   └── firestore.py         # Firestore adapter
    └── sched/
        └── scheduler.py         # Process-safe scheduler with file locks
```

## Key Design Decisions

### Stateless Workers

The application runs with multiple workers (`--workers 4`). All state is persisted externally:

- **User tokens**: Stored in JSON files under `APP_USER_DATA_DIR/<user_id>/credentials.json`
- **Scheduler**: Uses file-based locks (`fcntl.flock`) to ensure only one worker runs the scheduler
- **Firebase**: Initialized per-process via `firebase_admin`

### Authentication Flow

```
Client Request
    │
    ▼
Bearer Token in Authorization header
    │
    ▼
get_current_user_id() dependency
    │
    ├─► Firebase idToken verification (primary)
    │
    └─► Legacy token registry lookup (fallback)
    │
    ▼
user_id injected into route handler
```

### Error Handling

Exceptions follow a typed hierarchy rooted at `AppException`:

- `AuthException` → 401/403
- `StorageException` → 404/413/400
- `SchedulerException` → 404/500
- `ExternalServiceException` → 502
- `StartupException` → 500

The `error_handling_middleware` catches all unhandled exceptions and returns structured JSON responses.

### Security

- Input validation prevents path traversal (regex-based user_id and filename validation)
- Credentials encrypted with Fernet symmetric encryption
- Sensitive data redacted from logs (tokens, passwords)
- File permissions restricted (0o700 for user directories, 0o600 for credential files)
- Pickle deserialization disabled by default (`APP_ALLOW_UNSAFE_DESERIALIZE`)

### Concurrency

- Thread pool executor for blocking I/O (data loading)
- `threading.RLock` for shared state protection
- File-based scheduler lock for multi-process safety
- No shared mutable state between workers
