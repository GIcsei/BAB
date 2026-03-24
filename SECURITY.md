# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

- **Email**: security@example.com *(replace with your actual contact)*
- **Do not** open a public GitHub issue for security vulnerabilities.
- We aim to acknowledge reports within 48 hours and provide a fix within 7 days for critical issues.

## Secrets Management

- Service-account keys and other credentials **must** be mounted as volumes or injected via environment variables.
- Credentials **must never** be committed to source control.
- The application warns at startup if credential files are stored inside the project/source directory or have overly permissive file permissions.

## Key Rotation Policy

- Service-account keys should be rotated periodically.
- Default maximum credential age: **90 days**.
- Configurable via the `CREDENTIAL_MAX_AGE_DAYS` environment variable.
- The application logs a warning when a credential file exceeds the configured age threshold.

## Deserialization Policy

- Pickle / joblib deserialization is **not supported**. Only safe formats are accepted: CSV, Parquet, and JSON.
- Unsupported file formats are rejected at the API layer with an explicit error.

## Dependency Audit

- Run `pip-audit` periodically to detect known vulnerabilities in dependencies.
- All high/critical findings must be resolved before release.

## User Data Isolation

- User data is stored in per-user directories under the configured `APP_USER_DATA_DIR`.
- Path traversal protection: all user paths are resolved and verified to remain within the base data directory.
- Symlink-based escape attempts are detected and rejected.

## Logging Redaction

- Sensitive keys are automatically redacted from log output.
- Redacted keys include: `token`, `idToken`, `refreshToken`, `authorization`, `password`, `secret`, `credential`, `api_key`, `private_key`, `apikey`, `masterkey`, `master_key`.
- Structured JSON logging is available via `LOG_JSON=true`.
