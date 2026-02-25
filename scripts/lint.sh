#!/usr/bin/env bash
set -euo pipefail

uv run ruff check app tests
uv run black --check app tests