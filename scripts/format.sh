#!/usr/bin/env bash
set -euo pipefail

uv run black app tests
uv run ruff check --fix app tests