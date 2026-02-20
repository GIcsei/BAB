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
- [API Endpoints](#api-endpoints)
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

The repo contains `update.sh` to build images and launch development/productioncompose stacks. It uses the `pyproject.toml` version to tag images.

Development (interactive):


./update.sh
# follow prompt, enter 'dev' or 'prod'


Production mode uses `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` and expects environment variables to be supplied via your deployment pipeline.

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