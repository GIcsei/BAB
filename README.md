# Bank Analysis Backend

This README provides an overview, developer quickstart, API usage examples, and security/performance notes for the `bank_analysis_backend` FastAPI project. It documents updated runtime, configuration, and CI expectations introduced in recent changes:

- Python >= 3.12 (see `pyproject.toml`).
- Endpoints under `app/routers/data_plot.py` now require authentication and use `Authorization: Bearer <idToken>` header.
- The data service deserializes files via a controlled fallback and exposes async wrappers (`preview_pickle_file_async`, `extract_series_async`) to avoid blocking the FastAPI event loop.
- Pickle deserialization is potentially unsafe — see the Security section.

---

## Table of Contents

- [Quickstart (development)](#quickstart-development)
- [Configuration](#configuration)
- [Running locally (docker)](#running-locally-docker)
- [Running on TrueNAS SCALE](#running-on-truenas-scale)
- [API Endpoints](#api-endpoints)
- [AI Model Overview](#ai-model-overview)
- [Developer notes and code structure](#developer-notes-and-code-structure)
- [Testing and CI](#testing-and-ci)
- [Security considerations](#security-considerations)
- [Contributing and coding standards](#contributing-and-coding-standards)

---

## Quickstart (development)

1. Clone the repo and change to project dir:


   git clone https://github.com/GIcsei/BAB.git
   cd BAB


2. Create a virtual environment and install dependencies (project uses `pyproject.toml`):


   python -m venv .venv
   source .venv/bin/activate   # on Windows use `.venv\Scripts\activate`
   python -m pip install --upgrade pip
   python -m pip install -e .


3. Set required environment variables for local dev (example):


   export APP_USER_DATA_DIR=$(pwd)/user_data
   export APP_JOB_HOUR=18
   export APP_JOB_MINUTE=0
   export LOG_LEVEL=DEBUG


4. Run the app with uvicorn for development:


   uvicorn app.main:app --reload --port 8000


5. Open interactive docs:

- Open `http://localhost:8000/docs` (Swagger UI) or
- `http://localhost:8000/redoc`

## Configuration

Key environment variables (defaults shown):

- `APP_USER_DATA_DIR` (default: `/var/app/user_data`) — per-user data directory where credentials and pickles are stored.
- `APP_JOB_HOUR` (default: `18`) — hour for daily scheduled jobs.
- `APP_JOB_MINUTE` (default: `0`) — minute for daily scheduled jobs.
- `LOG_LEVEL` (default: `DEBUG`) — logging level.
- `LOG_FILE` (default: unset) — if set, logs rotate to this file; otherwise, logs stream to stdout.

These variables are read by `app/main.py` during startup. Job restore and token loading also occur on startup (these behaviors are safeguarded by tests/mocks).

## Running locally (docker)

The repo contains `update.sh` to build images and launch development/production compose stacks. It uses the `pyproject.toml` version to tag images.

Development (interactive):


./update.sh
# follow prompt, enter 'dev' or 'prod'


Production mode uses `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` and expects environment variables to be supplied via your deployment pipeline.


## Running on TrueNAS SCALE

To run this project reliably on TrueNAS SCALE, use the dedicated compose file and env template added for NAS deployment:

1. Copy `truenas.env.example` to `truenas.env` and set dataset paths (`APP_USER_DATA_HOST_PATH`, `APP_DOWNLOADS_HOST_PATH`) and `NETBANK_MASTER_KEY`.
2. Use `docker-compose.truenas.yml` in TrueNAS Custom App / Docker Compose stack configuration.
3. Keep container UID/GID aligned with TrueNAS apps user (`PUID=568`, `PGID=568` by default).
4. Store secrets outside the repository and mount them read-only (for example under `/mnt/<pool>/apps/bab/secrets`).

The container now supports runtime UID/GID remapping through `PUID`/`PGID` so mounted datasets remain writable without running your app process as root.

The published runtime image already contains application code. The `dockerfile` keeps `COPY app ./app` so self-built images remain runnable without host source mounts; only `docker-compose.dev.yml` uses bind mounts for live development reload.

## API Endpoints (updated)

All endpoints require a valid Firebase `idToken` in the `Authorization` header: `Authorization: Bearer <idToken>`.

Base prefix: `/data`

1. List authenticated user's pickles

   - GET `/data/list`
   - Description: Lists `.pkl`/`.pickle` files in the current user's data folder.
   - Example:


  curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/data/list"


2. Preview a pickle

- GET `/data/files/{filename}/preview?rows=<n>`
- Description: Returns a JSON-serializable preview of the object stored in the requested file. Rows are truncated to limit payload size.
- Example:


  curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/data/files/mydata.pkl/preview?rows=100"


3. Extract series for plotting

- GET `/data/files/{filename}/series?y=<y>&x=<x>&max_points=<n>`
- Required query parameter: `y` (column or series to use as Y). `x` is optional; if omitted, the handler will try the DataFrame index or `date` column.
- Example:


  curl -H "Authorization: Bearer $TOKEN" "http://localhost:8000/data/files/mydata.pkl/series?y=close&max_points=5000"


Notes on authentication and authorization:

- The project uses `app/core/auth.py`, which relies on the Firebase singleton in `app/core/firestore_handler/QueryHandler.py`.
- Routes now use `Depends(get_current_user_id)` to enforce that the caller is authenticated and to scope file access to the authenticated user's folder.

## AI Model Overview

This project contains the code and services required to host an AI-assisted data analysis model that authenticates users, loads per-user pickled datasets, extracts numeric series for plotting, and exposes those capabilities via authenticated HTTP endpoints.

### Model components

- **API / Router**: `app/routers/data_plot.py` — Exposes model functionality (file listing, preview, series extraction) via authenticated endpoints. Endpoints accept `Authorization: Bearer <idToken>` and validate input to prevent path traversal.

- **Application Entrypoint**: `app/main.py` — Configures logging, environment, startup tasks (job restore, token loading), and mounts the FastAPI app including middleware and dependency wiring for authentication.

- **Authentication**: `app/core/auth.py` and `app/core/firestore_handler/QueryHandler.py` — Handle Firebase `idToken` verification, login token persistence, per-user token registry, and token refresh workflows used to secure model access.

- **Firestore / Persistence Layer**: `app/core/firestore_handler/FirestoreService.py`, `DatabaseHandler.py`, and `DataDescriptor.py` — Abstract document/collection access and provide a lightweight interface to persist model metadata and user pointers to stored data.

- **Data Service (Model I/O)**: `app/services/data_service.py` — Safely loads serialized objects (joblib, pandas, pickle), performs controlled preview and numeric series extraction, and exposes async wrappers to avoid blocking the event loop.

- **Scheduler / Background Jobs**: `app/services/scheduler.py` — Single-process scheduler that runs periodic maintenance and spawns background workers for heavy tasks, protecting the main request loop.

- **Login / Token helpers**: `app/services/login_service.py` — High-level helpers for sign-in flows and token lifecycle management used by frontends and internal services.

- **Utilities**: `app/core/firestore_handler/Utils.py` and other helpers — Provide small, reusable functions for validation, path handling, and defensive checks used across the model.

- **Tests**: `tests/` (e.g. `test_data_plot.py`, `test_data_service.py`, `test_data_descriptor.py`) — Unit and integration tests that verify deserialization, API behavior, token handling, and core data transformations expected of the model.

- **CI / Deployment**: `.github/workflows/ci.yml`, `docker-compose.yml`, and `update.sh` — CI validates linting, typing, security scans and tests; Docker files and compose orchestrate local/dev/production deployments for the model.

- **Security & Standards**: `README.md` Security section, `.editorconfig`, and `CONTRIBUTING.md` — Document risky operations (pickle deserialization), safe practices, formatting rules, and contribution/testing expectations for maintaining the model securely.

## Developer notes and code structure

High-level layout of important modules:

- `app/main.py` — application entrypoint, logging setup, startup event that restores scheduled jobs and loads tokens.
- `app/routers/data_plot.py` — data endpoints (list, preview, series). Endpoints are async and validate inputs to avoid path traversal.
- `app/services/data_service.py` — core logic for listing files, loading serialized objects, converting to JSON, and extracting numeric series. Notable changes:
- `_try_load(path: Path)` tries `joblib.load` (if available), then `pandas.read_pickle`, then `pickle.load` as a last resort.
- `preview_pickle_file_async` and `extract_series_async` are async wrappers that execute blocking work in a thread pool to avoid blocking the FastAPI event loop.
- `_validate_file_size(path: Path, max_size_mb: int = 500)` to defend against very large file loads.
- `app/core/firestore_handler/DataDescriptor.py` — `Document` dataclass and `Collection` helpers. Recent fixes:
- `__repr__` returns a concise single-line representation.
- `from_dict` validates required keys explicitly.
- `Collection.update_elems` now preserves list semantics and supports `int`, `slice`, and `list/tuple` selectors safely.
- `app/services/scheduler.py` — single-process scheduler that sleeps until the next run; spawns background threads for heavy work. It was refactored to be defensive and log important events.

## Testing and CI

Tests live under `tests/`. Use `pytest` to run unit and integration tests. Example:


pytest -q --maxfail=1


CI is defined in `.github/workflows/ci.yml`. The workflow:

- Runs on `push`/`pull_request` to `main`.
- Uses Python 3.12 (aligns with `pyproject.toml`).
- Installs the project and dev tools: `pytest`, `mypy`, `flake8`, `bandit`, `pip-audit`.
- Runs formatters/linting, static typing, security scans, and tests with coverage.

Recommendation: run `pytest --cov=app --cov-report=term-missing` locally and ensure the coverage threshold required by CI is met.

## Security considerations (important)

- Never commit service-account credentials or private keys into the repository. Keep them in TrueNAS datasets/secrets and mount them read-only at runtime.
- Rotate and revoke any previously committed credentials immediately.
- Pickle and joblib can execute arbitrary code during deserialization. The codebase attempts to be defensive, but you must treat untrusted pickles as dangerous.
  - Prefer safe upload formats (Parquet, CSV, JSON) when possible.
  - If you must support pickle, restrict uploads to trusted users and run deserialization in an isolated environment (sandbox, separate process, or container) with resource limits.
- Input validation: all endpoints validate `filename` and `user_id` against restrictive regexes to prevent path traversal.
- Authentication: endpoints use Firebase `idToken` verification; never bypass `Depends(get_current_user_id)`.
- Resource quotas: enforce file-size limits and use thread pools/worker pools to avoid event-loop blocking and DoS from expensive deserialization.
- Do not log secrets (tokens, passwords) — log redacted values where necessary.

## Contributing and coding standards

- See `CONTRIBUTING.md` for contribution rules, tests, typing, and CI expectations.
- The project includes an `.editorconfig` file with formatting rules (4-space indent, max line length 120 for Python).
- All new code should include type annotations and be covered by tests where possible.

---