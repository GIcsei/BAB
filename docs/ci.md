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

Triggered by version tags (`v*`). Performs comprehensive validation and release publishing:

#### Validation Phase
- **Version sync**: Extracts tag version and compares to `pyproject.toml`. Release fails if versions mismatch.
- **Lint, type check, tests**: Runs full CI suite with 70% coverage minimum.
- **Security scanning** (blocks release on violations):
  - `pip-audit`: No known CVEs in dependencies.
  - `bandit`: No MEDIUM or CRITICAL code security issues.
  - Trivy: No HIGH or CRITICAL OS/library vulnerabilities in Docker image.

#### Release Phase
- Builds and pushes Docker image to Docker Hub (`icseig/bank_analysis_backend:vX.Y.Z`).
- Creates GitHub Release with auto-generated changelog.
- Generates and publishes HTML security reports to GitHub Pages at `/reports/security/vX.Y.Z/`.
- Updates `latest` symlink to point to the newest release.

**Required secrets** (configure in *Settings → Secrets and variables → Actions*):

| Secret | Description |
|--------|-------------|
| `DOCKERHUB_USERNAME` | Docker Hub username (e.g. `icseig`) |
| `DOCKERHUB_TOKEN` | Docker Hub access token (create at <https://hub.docker.com/settings/security>) |

#### Troubleshooting Release Failures

**Version sync check fails**: Ensure tag matches `pyproject.toml` version. Create tag as `v` + version string (e.g. tag `v1.2.3` for version `1.2.3`).

**pip-audit blocks release**: A Python dependency has a known CVE. Review the report, update the affected package in `pyproject.toml`, and commit before re-tagging.

**bandit blocks release**: Static analysis found MEDIUM or CRITICAL code security issues. Review `bandit-report.json`, fix the issues, and re-tag.

**Trivy blocks release**: Docker image has HIGH or CRITICAL OS/library vulnerabilities. Update the base image or vulnerable dependencies, rebuild, and re-tag.

### Docker Build & Push (Reusable Workflow: `docker-build-push.yml`)

Encapsulates Docker build, scan, and push logic used by both `docker.yml` and `release.yml`.

**Inputs**:
- `dockerfile_path`: Path to Dockerfile (default: `docker/Dockerfile`).
- `image_name`: Docker Hub image name (e.g. `icseig/bank_analysis_backend`).
- `tags`: Space-separated image tags to push.
- `push`: Boolean to enable Docker Hub push (default: `false`).
- `scan`: Boolean to run Trivy scan (default: `true`).

**Outputs**:
- `image_digest`: SHA256 digest of built image.
- `trivy_report`: Path to Trivy JSON report (if scanned).

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

## Security Gates and Blocking Criteria

The following conditions block CI/CD pipeline progression:

| Gate | Tool | Trigger | Consequence |
|------|------|---------|-------------|
| Linting | Ruff/Black | Main CI, Release | PR blocked, release aborted |
| Type checking | Mypy | Main CI, Release | PR blocked, release aborted |
| Test coverage | Pytest | Main CI, Release | PR blocked if < 70%, release aborted |
| Dependency CVEs | pip-audit | Main CI (informational), Release (blocking) | Release aborted on any CVE |
| Code security | bandit | Main CI (informational, LOW+), Release (blocking MEDIUM+) | Release aborted on MEDIUM/CRITICAL |
| Image security | Trivy | Main CI (blocking HIGH+), Release (blocking HIGH+) | Docker push blocked on HIGH/CRITICAL |

## GitHub Pages Publishing

Documentation and security reports are deployed to [GitHub Pages](https://gicsei.github.io/BAB/) automatically via `pages.yml`.

**Trigger**: Push to `main`, release tags, or manual dispatch.

**Published content**:
- `/`: MkDocs documentation (API, architecture, deployment, security, troubleshooting).
- `/reports/security/latest/`: Latest security scan reports (Trivy, bandit, pip-audit).
- `/reports/security/vX.Y.Z/`: Security reports for each release version.

**Report generation**: `scripts/generate-security-reports.py` converts JSON scan results (bandit, pip-audit, Trivy) into HTML reports.

## Adding or Modifying Workflows

- Keep workflows focused: one workflow per concern.
- Pin action versions to major tags (e.g. `actions/checkout@v4`).
- Use the `uv` cache to speed up dependency installation.
- Test workflow changes on a feature branch before merging to `main`.
