# Security Notes

## Overview

BAB follows defence-in-depth practices. This page documents the key security decisions, known risks, and recommendations for operators.

## Authentication & Authorisation

- All data endpoints require a valid Firebase `idToken` in the `Authorization: Bearer <token>` header.
- Tokens are verified against the Firebase Admin SDK; forged or expired tokens are rejected with `401`.
- User data is scoped strictly to the authenticated `user_id`; cross-user access is prevented by path-level and service-level checks.
- The `get_current_user_id` FastAPI dependency is the single enforcement point—**never bypass it**.

## Secret Management

- Firebase service-account credentials must **never** be committed to the repository.
- Secrets are supplied at runtime via environment variables or host-mounted read-only files.
- NetBank credentials are encrypted at rest with Fernet symmetric encryption (`NETBANK_MASTER_KEY`).
- Rotate and revoke any credential that has ever been committed to version control.

## Serialisation / Deserialisation Safety

- Pickle and joblib deserialisation can execute arbitrary code. This is **disabled by default** (`APP_ALLOW_UNSAFE_DESERIALIZE=false`).
- Prefer safe, schema-validated formats (Parquet, CSV, JSON) for user-provided data.
- If pickle support must be enabled, restrict it to trusted users and run deserialization in an isolated process with resource limits.

## Input Validation

- `user_id` and `filename` path parameters are validated against restrictive allow-list regexes to prevent path traversal attacks.
- Request body size is capped at `1,048,576` bytes (`1 MiB`) for `POST`, `PUT`, and `PATCH`; service-layer file-size guards remain in place for file processing paths.

## Logging & PII Redaction

- Tokens, passwords, and other sensitive values are automatically redacted before being written to logs.
- Avoid logging raw request/response bodies in production (`LOG_LEVEL=INFO` or higher).

## Container Hardening

- The production container runs as a non-root user (`appuser`) after UID/GID remapping via `gosu`.
- File permissions are restricted: `0o700` for user directories, `0o600` for credential files.
- Pickle deserialization is disabled by default inside the container.
- Base image and Python dependencies are scanned for known CVEs by Trivy (Docker workflow) and `pip-audit` (CI).

## CI Security Scanning

The CI/CD pipeline includes three layers of security scanning:

### pip-audit: Dependency Vulnerability Scan

| Aspect | Details |
|--------|----------|
| **Tool** | pip-audit |
| **Purpose** | Detect known CVEs in Python dependencies |
| **Trigger** | Every CI run and on release |
| **Main branch** | Informational; does not block merges |
| **Release** | **Blocking**: release aborted if any CVE found |
| **Report** | Available in CI artifacts and published to GitHub Pages on release |

**Fix**: Update vulnerable package in `pyproject.toml`, commit, and re-tag release.

### bandit: Static Code Security Analysis

| Aspect | Details |
|--------|----------|
| **Tool** | bandit |
| **Purpose** | Detect common Python security anti-patterns |
| **Trigger** | Every CI run and on release |
| **Main branch** | Reports all issues (LOW+); does not block |
| **Release** | **Blocking**: aborts if MEDIUM or CRITICAL issues found |
| **Report** | JSON format in artifacts; HTML report published to GitHub Pages on release |
| **Severity levels** | LOW, MEDIUM, HIGH, CRITICAL |

**Fix**: Review `bandit-report.json`, fix code issues (e.g., hardcoded secrets, SQL injection), commit, and re-tag.

### Trivy: Docker Image Vulnerability Scan

| Aspect | Details |
|--------|----------|
| **Tool** | Trivy |
| **Purpose** | Scan base image and installed libraries for OS/library CVEs |
| **Trigger** | Docker build on main branch push; release image build |
| **Main branch** | **Blocking**: aborts if HIGH or CRITICAL vulnerability found |
| **Release** | **Blocking**: aborts if HIGH or CRITICAL vulnerability found |
| **Report** | JSON format; HTML report published to GitHub Pages on release |
| **Severity levels** | LOW, MEDIUM, HIGH, CRITICAL |

**Fix**: Update base Docker image (see `Dockerfile`) or vulnerable dependencies, rebuild, and re-tag.

### Security Reports on GitHub Pages

After a successful release, all three scan reports are published in HTML format at:

```
https://gicsei.github.io/BAB/reports/security/vX.Y.Z/
```

Reports include:
- `trivy.html`: OS/library CVE scan results
- `bandit.html`: Code security issues
- `pip-audit.html`: Dependency vulnerabilities

The `latest/` directory is a symlink to the most recent release.

## Dependency Policy

- Dependencies are pinned via `uv.lock` and must be updated deliberately.
- Run `uv run pip-audit` locally before bumping dependencies.
- Review `bandit` output (`bandit-report.json` artifact) after each CI run.
- Before releasing, ensure all three security gates pass (pip-audit, bandit MEDIUM+, Trivy HIGH+).

## Reporting Vulnerabilities

Please report security issues privately via the [GitHub Security Advisory](https://github.com/GIcsei/BAB/security/advisories/new) form rather than opening a public issue.
