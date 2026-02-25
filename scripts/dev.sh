#!/usr/bin/env bash
set -euo pipefail

APP_PORT="${APP_PORT:-8000}"
uv run uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT}" --reload