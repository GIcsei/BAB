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
- Request body sizes are bounded by FastAPI/Starlette defaults and service-layer file-size guards.

## Logging & PII Redaction

- Tokens, passwords, and other sensitive values are automatically redacted before being written to logs.
- Avoid logging raw request/response bodies in production (`LOG_LEVEL=INFO` or higher).

## Container Hardening

- The production container runs as a non-root user (`appuser`) after UID/GID remapping via `gosu`.
- File permissions are restricted: `0o700` for user directories, `0o600` for credential files.
- Pickle deserialization is disabled by default inside the container.
- Base image and Python dependencies are scanned for known CVEs by Trivy (Docker workflow) and `pip-audit` (CI).

## CI Security Scanning

| Tool | Purpose | Trigger |
|------|---------|---------|
| `pip-audit` | Known CVEs in Python dependencies | Every CI run |
| `bandit` | Static analysis for common Python security anti-patterns (medium+ severity) | Every CI run |
| Trivy | OS + library CVE scan of the production Docker image | Push to `main` |

## Dependency Policy

- Dependencies are pinned via `uv.lock` and must be updated deliberately.
- Run `uv run pip-audit` locally before bumping dependencies.
- Review `bandit` output (`bandit-report.json` artifact) after each CI run.

## Reporting Vulnerabilities

Please report security issues privately via the [GitHub Security Advisory](https://github.com/GIcsei/BAB/security/advisories/new) form rather than opening a public issue.
