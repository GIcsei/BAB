# ACTIVE TASK

- Task ID: BAB-DOCKER-UV-BUILD-2026-05-14
- Request: Fix GitHub Docker build failure where `uv pip install -e .` cannot find a virtual environment in the builder stage.
- Owner: scrum-master
- Stage: tester-pass-caveat
- Priority: high
- Started: 2026-05-14

## Acceptance Criteria

[x] Docker builder no longer uses a uv install mode that requires auto-detected active venv.
[x] Change is minimal and runtime behavior is preserved.
[x] Patch version increase is applied for bug-fix change.
[x] Focused tester validation passes in local/dev scope.
[ ] Full Docker builder completion is confirmed in CI/build host.

## Evidence

- Implementation change: `docker/Dockerfile` now uses `uv pip install --python /opt/venv/bin/python -e .` instead of `uv pip install -e .`.
- Versioning change: `pyproject.toml` bumped from `1.0.10` to `1.0.11` (patch fix).
- Tester validation: confirmed `uv pip --help` supports `--python`; local editable install succeeded with `uv pip install --python .\\.venv\\Scripts\\python.exe -e .`.
- Container validation attempt: `docker build --target builder -f docker/Dockerfile .` reached step `[6/8] RUN uv sync --frozen --no-dev` before terminal interruption; step `[7/8]` not observed to completion in-session.
