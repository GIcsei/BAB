# Troubleshooting & FAQ

## Common Issues

### Application won't start

**Symptom**: `uvicorn` exits immediately or the `/health` endpoint returns `503`.

**Possible causes**:

1. **Missing environment variables** — ensure `.env` is present and contains at least `APP_USER_DATA_DIR`. See [Setup](setup.md) for the full variable list.
2. **Firebase credentials not found** — set `FIRESTORE_CREDENTIALS` to the path of your service-account JSON file. In Docker, mount it read-only.
3. **Port already in use** — change `APP_PORT` or stop the conflicting process.

### Firebase authentication errors

**Symptom**: `401 INVALID_TOKEN` on every request.

- Verify the Firebase service-account JSON matches the project that issued the `idToken`.
- Check that the token has not expired (default lifetime is 1 hour).
- Ensure the server clock is synchronised (Firebase rejects tokens with excessive clock skew).

### Pickle deserialization disabled

**Symptom**: `403 DESERIALIZATION_DISABLED` when previewing or extracting series from `.pkl` files.

- Pickle deserialization is **disabled by default** for security.
- Set `APP_ALLOW_UNSAFE_DESERIALIZE=true` in `.env` to enable it.
- Prefer safe formats (CSV, Parquet) when possible.

### Docker container permission errors

**Symptom**: `PermissionError` when the container writes to mounted volumes.

- Set `PUID` and `PGID` to match the host user that owns the mount points.
- On TrueNAS, use `PUID=568` / `PGID=568` (default apps user).
- Ensure host directories exist before starting the container.

### Tests fail locally but pass in CI

- Confirm you are using Python 3.12 (`python --version`).
- Install dev dependencies: `uv sync --frozen --group dev`.
- Set `PYTEST_RUNNING=1` if tests depend on test-mode behaviour.
- Run with the same flags CI uses:
  ```bash
  uv run pytest -v --maxfail=1 --cov=app --cov-fail-under=70
  ```

### MkDocs build fails

- Install the theme: `pip install mkdocs-material`.
- Run `mkdocs build --strict` to see detailed errors.
- Check that all files referenced in `mkdocs.yml` `nav` exist in `docs/`.

---

## FAQ

### How do I add a new API endpoint?

1. Create or extend a router in `app/routers/`.
2. Delegate business logic to a service in `app/services/`.
3. Define request/response schemas in `app/schemas/`.
4. Register the router in `app/main.py`.
5. Add tests in `tests/functionaltest/` and/or `tests/unittest/`.
6. Document the endpoint in `docs/api.md`.

### How do I update the documentation site?

Edit files in `docs/`, update `mkdocs.yml` if adding new pages, and merge to `main`. The GitHub Pages workflow deploys automatically. See [CONTRIBUTING.md](https://github.com/GIcsei/BAB/blob/main/CONTRIBUTING.md) for local preview instructions.

### How do I run a one-off data collection for a user?

Use the `PUT /user/collect_automatically` endpoint with a valid Bearer token. This triggers an immediate collection run for the authenticated user.

### Where are logs stored?

By default, logs go to stdout (Docker-friendly). Set `LOG_FILE` to write to a file, and `LOG_JSON=true` for structured JSON output.

### How is stale data handled?

The deletion worker runs periodically and removes user-linked transient data after the configured inactivity threshold (default: 7 days). The threshold is configurable via `INACTIVE_DATA_TTL_DAYS`. Monitor deletion metrics at `GET /admin/cleanup-metrics`.

### How do I report a security issue?

Use the [GitHub Security Advisory](https://github.com/GIcsei/BAB/security/advisories/new) form. Do not open a public issue for security vulnerabilities.
