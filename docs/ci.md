# CI/CD Pipeline

## Overview

The project uses GitHub Actions for continuous integration, documentation deployment, Docker image publishing, and releases. All workflow definitions live in `.github/workflows/`.

## Workflows

### CI (`ci.yml`)

Runs on every push and pull request to `main`.

| Job | Purpose |
|-----|---------|
| **lint** | Ruff + Black formatting checks |
| **typecheck** | Mypy strict mode |
| **test** | Pytest with 70 % minimum coverage, HTML report generation |
| **security** | `pip-audit` (dependency CVEs) + `bandit` (static analysis, medium+ severity) |
| **build** | Docker image build (main branch only, after all checks pass) |
| **notify** | Comments on PRs when jobs fail |

**Artifacts produced**: test reports, coverage reports (XML + HTML), bandit report (JSON), documentation snapshot.

### GitHub Pages (`pages.yml`)

Deploys documentation to [GitHub Pages](https://gicsei.github.io/BAB/).

- **Trigger**: push to `main`, release tags (`v*`), or manual dispatch.
- **Process**: installs MkDocs Material, runs `mkdocs build --strict`, uploads the `site/` directory as a Pages artifact, and deploys.
- **Concurrency**: only one Pages deployment runs at a time; in-progress runs are not cancelled to avoid partial deployments.

### Docker (`docker.yml`)

Builds and optionally pushes Docker images for the application.

### Release (`release.yml`)

Triggered by version tags (`v*`). Runs the full validation suite (lint, typecheck, tests, security), then:

1. Builds and pushes a Docker image to Docker Hub (`icseig/bank_analysis_backend`).
2. Creates a GitHub Release with auto-generated changelog.

**Required secrets** (configure in *Settings → Secrets and variables → Actions*):

| Secret | Description |
|--------|-------------|
| `DOCKERHUB_USERNAME` | Docker Hub username (e.g. `icseig`) |
| `DOCKERHUB_TOKEN` | Docker Hub access token (create at <https://hub.docker.com/settings/security>) |

## Running Checks Locally

Replicate CI checks on your machine:

```bash
# Lint
uv run ruff check app tests
uv run black --check app tests

# Type check
uv run mypy app

# Tests with coverage
uv run pytest -v --cov=app --cov-fail-under=70

# Security
uv run pip-audit
uv run bandit -r app -ll
```

## Adding or Modifying Workflows

- Keep workflows focused: one workflow per concern.
- Pin action versions to major tags (e.g. `actions/checkout@v4`).
- Use the `uv` cache to speed up dependency installation.
- Test workflow changes on a feature branch before merging to `main`.
