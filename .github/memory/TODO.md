## TODO — Security & Bug Findings (Audit 2026-05-08)

### Docker uv Builder Failure Snapshot (2026-05-14)

- User report: GitHub Docker build failed at builder step with `uv pip install -e .` error `No virtual environment found`.
- Implementation owner: `platform-infrastructure`.
- Contract delta: `docker/Dockerfile` now installs editable package with explicit interpreter path (`uv pip install --python /opt/venv/bin/python -e .`).
- Versioning delta: `pyproject.toml` patch bump `1.0.10 -> 1.0.11`.
- Tester gate: focused pass for uv CLI semantics and local editable install path; full container builder completion remains pending CI/build-host run.
- Status: Implemented (tester-pass with caveat).

### Firestore Token-Expiry Scheduler Incident (2026-05-14)

- User report: after ~1 day inactivity, scheduler OTP polling repeatedly receives Firestore `401 UNAUTHENTICATED` until user logs in again.
- Implementation owner: `platform-infrastructure`.
- Contract delta: active-user token selection now refreshes expired tokens during `set_active_user` before Firestore query use.
- Test coverage delta: added expired-token refresh success/failure tests in `tests/unittest/test_query_handler.py`.
- Tester gate: passed (`tests/unittest/test_query_handler.py` 29 passed; token expiry adjacent slice 2 passed; `tests/integrationtest/test_query_handler_extended.py` 10 passed).
- QA gate: conditional pass with recommendation for rollout monitoring and optional >24h idle soak scenario.
- Status: Completed (conditional-pass).

### Health Version Readout Snapshot (2026-05-10)

- User request: add BAB version readout possibility to `/health`.
- Implementation owner: `api-surface`.
- Contract delta: `/health` now includes `version` in both `200` and `503` responses.
- Tester gate: passed (`3` focused endpoint tests + `10` health unit tests).
- Documentation sync: completed in `docs/api.md`.
- Status: Completed.

### CI/CD Recovery Snapshot (2026-05-10)

- User-requested full verification run executed by `tester` using CI-equivalent commands.
- Pytest gate: failed early at `tests/functionaltest/test_feature_enhancements.py` (`expected 200, got 400`).
- Bandit gate: failed with medium B310 at `app/core/health.py`.
- Mypy gate: failed with `no-untyped-call` at `app/core/firestore_handler/Utils.py`.
- Next handoff: `backend-implementer` for minimal CI blocker remediation, then `tester` re-run.
- Status: Completed.
- Implemented fix: `app/core/netbank/getReport.py` exception path in `_handle_already_logged_in_Selenium` no longer masks failures.
- Final verification: `uv run pytest -q` (`625 passed, 2 skipped, 1 warning`), CI-style pytest (`625 passed, 2 skipped, 1 warning`), `uv run bandit -r app -ll` (pass), `uv run mypy app` (pass).

### Execution Status Snapshot (2026-05-08)

- Overall program status: In Progress (delegated sequencing underway).
- Current owner: scrum-master.
- Next handoff: tech-lead (define smallest-first implementation sequence).
- Dependency freshness/web vulnerability verification: Pending and required before dependency changes.

### Release Stability Sprint Snapshot (2026-05-10)

- T-07 Phase 1 Firestore consolidation: Completed (owner: backend-implementer).
- T-07 tester gate: Passed in focused scope (25 passed, 0 failed, 0 skipped).
- T-07 QA gate: Conditional pass with residual field-preservation risk noted for populated `users/{user_id}` documents.
- T-08 Phase 2 logging/auth/scheduler reliability: Completed (owner: backend-implementer).
- T-08 Phase 2 hardening follow-up: Completed (owner: backend-implementer).
- T-08 tester second-run peer review: Passed (focused 16 passed + broader targeted 78 passed, 0 failed).
- T-08 security follow-up: Conditional pass; relative-expiry ambiguity closed and non-`fcntl` risk reduced with explicit env override guardrail.
- T-08 QA final decision: Conditional pass; release-time guardrails required for non-`fcntl` override governance.
- Post-T-08 scheduler hotfix: Completed. Same-user duplicate immediate triggers are deduped in-flight to prevent overlapping runs.
- Post-T-08 tester gate: Passed (`tests/unittest/test_scheduler_extended.py`, `tests/unittest/test_scheduler.py`, `tests/unittest/test_scheduler_worker.py`, `tests/unittest/test_scheduler_coverage.py` -> 51 passed).
- T-09 Phase 3 parquet streaming and access controls: implementation complete; QA review pending.
- T-10 Phase 4 Docker/CI release hardening: completed.
- Focused validation for T-07: `tests/unittest/test_firestore_service.py`, `tests/unittest/test_registration_service.py`, `tests/unittest/test_login_service.py`, `tests/unittest/test_login_service_extended.py` -> 42 passed.
- Focused validation for T-08: `tests/integrationtest/test_query_handler_extended.py`, `tests/unittest/test_scheduler_extended.py`, `tests/functionaltest/test_main_startup.py` -> 27 passed.
- Adjacent compatibility validation for T-08: `tests/unittest/test_coverage_gaps_extended.py`, `tests/integrationtest/test_query_handler_coverage.py` -> 17 passed, 1 warning.

### Track 1 Status

- C-2 FIREBASE_API_KEY TrueNAS wiring: Completed (owner: platform-infrastructure).
- Dependency freshness/web vulnerability check: Completed (owner: security-engineer).
- L-1 legacy `parquet` dependency removal: Completed.
- C-1 .env tracking safeguard: Completed.
- C-3 short-term worker pinning: Completed.
- H-1 SELENIUM_REMOTE_URL wiring: Completed.
- M-7 TrueNAS remap start requirement: Completed.
- L-3 APP_UNREGISTER_DELETION_DAYS template doc: Completed.
- Next queued: security hardening bundle (C-4, H-2, H-3, H-4, H-5, H-7, H-8, M-2, M-9).

### Security Bundle Status

- C-4 auth endpoint rate limiting: Completed.
- H-2 temp token file race fix: Completed.
- H-3 download permission tightening: Completed.
- H-4 deletion pending file permissions: Completed.
- H-5 cross-domain redirect auth forwarding safety: Completed.
- H-7 netbank credential bounds: Completed.
- H-8 login/register password bounds: Completed.
- M-2 login/register internal error leakage reduction: Completed.
- M-9 token/credential file restrictive permissions hardening: Completed (minimum-risk step).

### Validation Follow-up

- QA-requested Windows symlink-hardening deterministic behavior: Completed.

### Remaining Unresolved Sequence

- Track 1 (backend-implementer): Completed.
- Track 2 (api-surface): Completed.
- Track 3 (platform-infrastructure): Completed.
- Track 4 (security tail): Completed.
- Phase 4 Docker/CI release follow-up: completed.

### Closure

- Documentation synchronization: Completed.
- Open-point execution cycle: Completed.

> Objective: ensure BAB is production-safe on TrueNAS, debuggable on Linux and Windows.
> Severity: **CRITICAL** · **HIGH** · **MEDIUM** · **LOW**
> Effort: **Trivial** (< 1h) · **Low** (half day) · **Medium** (1-2 days) · **High** (> 2 days)

---

### 🔴 CRITICAL

---

#### C-1 — `.env` committed to the repository
| | |
|---|---|
| **Severity** | CRITICAL |
| **Effort** | Trivial |
| **File** | [.gitignore](.gitignore) · [.env](.env) |

`.gitignore` excludes `.env.*` but **not `.env`** itself, so the file is tracked by git.
Even though the current `.env` contains only placeholder paths (no real secrets), this pattern is dangerous: a developer filling in real values will silently commit them.
The `.env` file must be excluded from git and an `.env.example` template committed instead.

**Fix:** Add `.env` to `.gitignore`. Rename the current file to `.env.example` and strip any real values.

---

#### C-2 — `FIREBASE_API_KEY` missing from TrueNAS env template — startup fails silently
| | |
|---|---|
| **Severity** | CRITICAL |
| **Effort** | Trivial |
| **File** | [truenas.env.example](truenas.env.example) · [docker/docker-compose.truenas.yml](docker/docker-compose.truenas.yml) · [app/core/firestore_handler/QueryHandler.py](app/core/firestore_handler/QueryHandler.py#L38) |

`Firebase.__init__` requires `FIREBASE_API_KEY` either in the service-account JSON (`apiKey` field) or as an environment variable.
Firebase service-account JSON files do **not** contain `apiKey`; the Web API key must be supplied separately.
Neither `truenas.env.example` nor `docker-compose.truenas.yml` sets this variable, so every fresh TrueNAS deployment crashes at startup with `ValueError: FIREBASE_API_KEY is not configured`.

**Fix:** Add `FIREBASE_API_KEY=<web-api-key>` to `truenas.env.example` and to the `environment:` block of `docker-compose.truenas.yml`.

---

#### C-3 — Multi-worker incompatibility: in-memory state not shared across workers
| | |
|---|---|
| **Severity** | CRITICAL |
| **Effort** | Low |
| **File** | [docker/Dockerfile](docker/Dockerfile#L54) · [app/application/services/token_service.py](app/application/services/token_service.py) · [app/core/netbank/credentials.py](app/core/netbank/credentials.py) |

The Dockerfile CMD launches **4 uvicorn workers** (`--workers 4`).  Each OS process has its own Python interpreter with its own copy of `_DEFAULT_FIREBASE`, `TokenRegistry`, and `_CREDENTIAL_CACHE`.
A user who logs in via worker-1 has their token stored only in worker-1's memory; the next request routed to worker-2 returns 401.
TrueNAS compose overrides to `--workers 1`, avoiding the bug there, but the default image and dev compose do not.

**Fix (short-term):** Pin `--workers 1` in the Dockerfile CMD.  
**Fix (long-term):** Persist tokens to disk (already partially done via `credentials.json`) and always reload from disk on token miss, or use Redis as shared session store.

---

#### C-4 — No rate limiting on authentication endpoints
| | |
|---|---|
| **Severity** | CRITICAL |
| **Effort** | Low |
| **File** | [app/routers/login.py](app/routers/login.py#L70) |

`POST /user/login`, `POST /user/register`, and `POST /user/password-reset` have no rate limiting.
An attacker can perform unlimited credential-stuffing or brute-force attempts with no throttle, lockout, or CAPTCHA.
This is OWASP API4:2023 (Unrestricted Resource Consumption) and OWASP A07:2021 (Identification and Authentication Failures).

**Fix:** Add [`slowapi`](https://github.com/laurentS/slowapi) (already listed as a pattern in the ecosystem; add to `pyproject.toml`) with a per-IP limit (e.g. 5 req/min) on all auth endpoints.

---

### 🟠 HIGH

---

#### H-1 — `SELENIUM_REMOTE_URL` env var ignored — WebDriver URL hardcoded
| | |
|---|---|
| **Severity** | HIGH |
| **Effort** | Trivial |
| **File** | [app/core/netbank/getReport.py](app/core/netbank/getReport.py#L210) · [docker/docker-compose.yml](docker/docker-compose.yml#L18) |

`docker-compose.yml` sets `SELENIUM_REMOTE_URL=http://selenium:4444` but the application **never reads it**.
`getReport.py` hardcodes `command_executor="http://selenium:4444"`.
On Linux bare-metal, TrueNAS without Docker networking, or any environment where the Selenium host differs, the Selenium driver silently fails.

**Fix:** Replace the hardcoded string with `os.environ.get("SELENIUM_REMOTE_URL", "http://selenium:4444")` and document `SELENIUM_REMOTE_URL` in `truenas.env.example`.

---

#### H-2 — `auth_token_tmp.json` — shared temp file race condition
| | |
|---|---|
| **Severity** | HIGH |
| **Effort** | Low |
| **File** | [app/services/login_service.py](app/services/login_service.py#L68) |

Both `login_user()` and `register_user()` write to the **same** file `base_data_dir / "auth_token_tmp.json"`.
Under concurrent login requests (multiple users or retries) the file is overwritten mid-flight, corrupting the token before it is read back.

**Fix:** Use a per-request temp file (e.g. `tempfile.NamedTemporaryFile`) or generate a unique path per call (e.g. `base_data_dir / f"auth_token_{uuid.uuid4().hex}.json"`), then delete it after use.

---

#### H-3 — Download directory created world-writable (`0o777`)
| | |
|---|---|
| **Severity** | HIGH |
| **Effort** | Trivial |
| **File** | [app/core/netbank/getReport.py](app/core/netbank/getReport.py#L198) |

`ensure_directory()` calls `os.chmod(path, 0o777)` on the Selenium download directory.
Any OS-level process (including a compromised Selenium container) can write to this directory and replace the downloaded XLS report with a malicious file before the application processes it.

**Fix:** Change to `0o700` (owner read/write/execute only). Selenium writes under the container's own UID, which is the same as the app user when using shared volumes.

---

#### H-4 — `deletion_pending.json` written without restrictive permissions
| | |
|---|---|
| **Severity** | HIGH |
| **Effort** | Trivial |
| **File** | [app/services/user_deletion_service.py](app/services/user_deletion_service.py#L33) |

`schedule_user_deletion()` uses `open(pending_path, "w")` without setting file permissions, so the file inherits the process umask.  If `umask` is permissive (e.g. `0o022` in some Docker images), other processes can read or tamper with deletion timestamps.

**Fix:** Replace with `os.open(pending_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)` and `os.fdopen(fd, "w")`.

---

#### H-5 — `KeepAuthSession` forwards Authorization header on all redirects
| | |
|---|---|
| **Severity** | HIGH |
| **Effort** | Low |
| **File** | [app/core/firestore_handler/Utils.py](app/core/firestore_handler/Utils.py#L43) |

`KeepAuthSession.rebuild_auth` returns `None` unconditionally, meaning the `Authorization: Bearer <idToken>` header is **never stripped** on HTTP redirects, even cross-domain ones.
If a Firestore API call is redirected (e.g., by an attacker manipulating DNS or a misconfigured proxy), the user's Firebase idToken is forwarded to a third-party host.

**Fix:** Restore default `requests` behavior — only preserve Auth on same-domain redirects — or remove `KeepAuthSession` if it is not needed (Firestore REST API does not issue redirects).

---

#### H-6 — Firebase API key exposed in HTTP URL query string
| | |
|---|---|
| **Severity** | HIGH |
| **Effort** | Medium |
| **File** | [app/core/firestore_handler/User.py](app/core/firestore_handler/User.py#L34) · [app/core/firestore_handler/DatabaseHandler.py](app/core/firestore_handler/DatabaseHandler.py#L85) |

All Firebase Identity Toolkit REST calls append the API key as a URL query parameter (`?key=<API_KEY>`).
This means the key appears in web-server access logs, proxy logs, Selenium logs, and browser history — any component that records full URLs.
While Firebase API keys are not secret in the same sense as service-account keys, their exposure increases the attack surface for quota abuse and phishing Firebase projects.

**Fix (short-term):** Ensure `LOG_LEVEL` is `INFO` (not `DEBUG`) in production so URLs are not logged.  
**Fix (long-term):** Move API key to an `X-Goog-Api-Key` header where supported, or use the Firebase Admin SDK for all server-to-server calls.

---

#### H-7 — No input validation on `CredentialsIn` (netbank credentials)
| | |
|---|---|
| **Severity** | HIGH |
| **Effort** | Low |
| **File** | [app/schemas/netbank.py](app/schemas/netbank.py) · [app/routers/netbank_credentials.py](app/routers/netbank_credentials.py#L14) |

`CredentialsIn.username`, `account_number`, and `password` are bare `str` fields with no length or format constraints.
An attacker (or a UI bug) can submit kilobytes of data, which is encrypted and stored to disk without bounds checking, enabling disk exhaustion.

**Fix:** Add Pydantic `Field` validators: `username: str = Field(max_length=128)`, `account_number: str = Field(max_length=64)`, `password: str = Field(min_length=6, max_length=256)`.

---

#### H-8 — No password complexity or max-length validation on Register / Login
| | |
|---|---|
| **Severity** | HIGH |
| **Effort** | Low |
| **File** | [app/schemas/login.py](app/schemas/login.py#L9) |

`RegisterRequest.password` and `LoginRequest.password` have no minimum length, maximum length, or complexity constraints at the API layer.
Passwords of 1 character are accepted; passwords of arbitrary length could cause slowness or downstream Firebase limits to be hit without helpful error messages.

**Fix:** Add `password: str = Field(min_length=8, max_length=256)` to both schemas. Optionally add a regex validator for complexity.

---

### 🟡 MEDIUM

---

#### M-1 — `datetime.utcnow()` deprecated in Python 3.12
| | |
|---|---|
| **Severity** | MEDIUM |
| **Effort** | Trivial |
| **File** | [app/core/firestore_handler/User.py](app/core/firestore_handler/User.py#L56) |

`datetime.utcnow()` is deprecated since Python 3.12 and raises `DeprecationWarning` in every invocation; it will be removed in a future release, breaking the custom-token generation path.

**Fix:** Replace with `datetime.now(timezone.utc)`.

---

#### M-2 — Internal error details leaked to client
| | |
|---|---|
| **Severity** | MEDIUM |
| **Effort** | Trivial |
| **File** | [app/routers/login.py](app/routers/login.py#L90) · [app/routers/login.py](app/routers/login.py#L116) |

In the catch-all `except Exception` handlers, `str(exc)` is passed directly to `LoginFailedError(str(exc))` / `RegistrationFailedError(str(exc))` and surfaces in the HTTP 401 response body.
Internal messages (connection errors, missing env vars, Firebase error payloads) become visible to unauthenticated callers.

**Fix:** Log `exc` at ERROR level and return a generic `"Login failed"` / `"Registration failed"` message without the raw exception string.

---

#### M-3 — No HTTP request body size limit
| | |
|---|---|
| **Severity** | MEDIUM |
| **Effort** | Low |
| **File** | [app/main.py](app/main.py) |

FastAPI/Starlette has no default body size limit.  A client can POST a multi-megabyte JSON body to any endpoint, consuming memory and CPU before Pydantic validation rejects it.

**Fix:** Add a `ContentSizeLimitMiddleware` (available via `starlette_exceptionhandlers` or a small custom middleware) capping requests at e.g. 1 MB.

---

#### M-4 — CORS `allow_methods=["*"]` is overly permissive
| | |
|---|---|
| **Severity** | MEDIUM |
| **Effort** | Trivial |
| **File** | [app/main.py](app/main.py#L148) |

`allow_methods=["*"]` allows DELETE, PUT, PATCH, OPTIONS, etc. from any allowed origin.  The API only needs GET, POST, PUT, DELETE — restrict the list explicitly.

**Fix:** Replace with `allow_methods=["GET", "POST", "PUT", "DELETE"]`.

---

#### M-5 — `os.path.getctime` cross-platform inconsistency
| | |
|---|---|
| **Severity** | MEDIUM |
| **Effort** | Trivial |
| **File** | [app/core/netbank/getReport.py](app/core/netbank/getReport.py#L241) |

`max(files, key=os.path.getctime)` returns the **newest** file by creation time on Windows, but on Linux `getctime` returns the inode-change time, not the creation time.  After a file rename or attribute change, `getctime` could pick the wrong file.

**Fix:** Use `os.path.getmtime` (modification time) which behaves consistently on both platforms.

---

#### M-6 — Mutable default argument in `_file_exist_today`
| | |
|---|---|
| **Severity** | MEDIUM |
| **Effort** | Trivial |
| **File** | [app/core/netbank/getReport.py](app/core/netbank/getReport.py#L162) |

`def _file_exist_today(self, extension: List[str] = ["xls"])` — the default list is shared across all calls.  If any caller appends to it, the default is permanently mutated.

**Fix:** Change to `extension: Optional[List[str]] = None` and set `extension = extension or ["xls"]` inside the body.

---

#### M-7 — `PUID`/`PGID` remapping requires root — not guaranteed in TrueNAS
| | |
|---|---|
| **Severity** | MEDIUM |
| **Effort** | Low |
| **File** | [docker/entrypoint.sh](docker/entrypoint.sh#L14) · [docker/docker-compose.truenas.yml](docker/docker-compose.truenas.yml) |

`entrypoint.sh` remaps UID/GID only when `id -u == 0`.  TrueNAS Custom App may not start containers as root depending on the security profile.  If the container starts as the build-time `appuser` (UID 1200), `usermod`/`groupmod` are skipped and the volume mount at `PUID=568` will have permission errors.

**Fix:** Add `user: "0:0"` (or `privileged: true` temporarily) to `docker-compose.truenas.yml` so the entrypoint always starts as root and can safely remaps to the TrueNAS apps UID. Document this requirement clearly.

---

#### M-8 — Hardcoded Windows path as class attribute default in `reportFormatter`
| | |
|---|---|
| **Severity** | MEDIUM |
| **Effort** | Trivial |
| **File** | [app/core/netbank/utils.py](app/core/netbank/utils.py#L58) |

`reportFormatter.FOLDER = r"D:\Erste"` is a Windows absolute path set as a class-level default.  On Linux/TrueNAS it is never a valid directory and will cause silent errors if the constructor is ever called without an explicit `fileLoc`.

**Fix:** Change to `FOLDER: str = "/tmp/Erste"` (or derive from settings) and add a `__init__` guard that raises `ValueError` if `FOLDER` is still a Windows path on a non-Windows system.

---

#### M-9 — `credentials.json` (idToken + refreshToken) stored unencrypted on disk
| | |
|---|---|
| **Severity** | MEDIUM |
| **Effort** | Medium |
| **File** | [app/application/services/token_service.py](app/application/services/token_service.py#L42) · [app/services/login_service.py](app/services/login_service.py#L48) |

Firebase idTokens expire in 1 hour, but `refreshToken` is long-lived and stored in plain-text JSON.  Anyone with read access to the data volume (e.g. a TrueNAS admin browsing the dataset) can use the `refreshToken` to obtain fresh idTokens indefinitely.

**Fix:** Encrypt `credentials.json` using the same `Fernet` + `NETBANK_MASTER_KEY` pattern already in place for netbank credentials, or at minimum restrict file permissions to `0o600` (already done, but encryption is stronger).

---

#### M-10 — Log rotation not configured; unbounded log file growth
| | |
|---|---|
| **Severity** | MEDIUM |
| **Effort** | Low |
| **File** | [docker/docker-compose.truenas.yml](docker/docker-compose.truenas.yml#L22) · [app/core/logging_config.py](app/core/logging_config.py#L87) |

`LOG_FILE=/var/app/app.log` is set in the TrueNAS compose but `RotatingFileHandler` in `logging_config.py` uses default `maxBytes=0` (no rotation) and `backupCount=0`.  On a NAS with limited pool space, this file grows without bound.

**Fix:** Set `maxBytes=10_485_760` (10 MB) and `backupCount=5` in `configure_logging()`, or pass them as configurable env vars `LOG_MAX_BYTES` / `LOG_BACKUP_COUNT`.

---

#### M-11 — No Selenium health component in application health check
| | |
|---|---|
| **Severity** | MEDIUM |
| **Effort** | Low |
| **File** | [app/core/health.py](app/core/health.py) · [app/main.py](app/main.py#L184) |

`GET /health` reports `ready=true` even when the Selenium container is unreachable.  Scheduled jobs will silently fail until Selenium recovers, with no health-check signal to the orchestrator.

**Fix:** Add a `selenium` component to `HealthStatus.components`, probe `SELENIUM_REMOTE_URL/status` at startup (with a short timeout), and mark it ready or failed accordingly.

---

### 🔵 LOW

---

#### L-1 — `parquet` package is a redundant/outdated wrapper
| | |
|---|---|
| **Severity** | LOW |
| **Effort** | Trivial |
| **File** | [pyproject.toml](pyproject.toml#L21) |

`parquet>=1.3.1` is a thin legacy Python wrapper (last released 2016) that is **not** the actual Parquet engine.  `pyarrow>=23.0.1` (also listed) is the correct, modern library used by pandas.  Having both adds install weight without benefit; `parquet` may install conflicting binary blobs.

**Fix:** Remove `parquet` from `[project.dependencies]`.

---

#### L-2 — `_handle_already_logged_in_Selenium` logic bug in exception path
| | |
|---|---|
| **Severity** | LOW |
| **Effort** | Trivial |
| **File** | [app/core/netbank/getReport.py](app/core/netbank/getReport.py#L269) |

Inside the `except Exception` block: `return False or "checksession" in driver.current_url.lower()`.
This is equivalent to `return "checksession" in driver.current_url.lower()` — it returns `True` (session still usable) when the URL happens to contain `"checksession"` even after an exception, which can mask the real failure.  The intent appears to be `return False`.

**Fix:** Replace with `return False` inside the `except` block and handle the `checksession` URL check as an explicit condition in the normal path.

---

#### L-3 — `APP_UNREGISTER_DELETION_DAYS` not documented in TrueNAS env template
| | |
|---|---|
| **Severity** | LOW |
| **Effort** | Trivial |
| **File** | [truenas.env.example](truenas.env.example) · [app/core/config.py](app/core/config.py) |

`APP_UNREGISTER_DELETION_DAYS` controls how long before a user's data is permanently deleted after unregistration.  It defaults to an undocumented value and is not mentioned in `truenas.env.example`, so operators cannot tune data retention without reading source code.

**Fix:** Add `# APP_UNREGISTER_DELETION_DAYS=60` (commented out with default) to `truenas.env.example`.

---

#### L-4 — `HealthStatus.startup_complete_time` is timezone-naive
| | |
|---|---|
| **Severity** | LOW |
| **Effort** | Trivial |
| **File** | [app/core/health.py](app/core/health.py#L33) |

`mark_startup_complete()` calls `datetime.now()` (naive, local time) while `_startup_time` is `datetime.now(timezone.utc)` (aware).  Comparing or serialising them together will raise a `TypeError` in Python 3.12+ if they are ever subtracted.

**Fix:** Change to `self.startup_complete_time = datetime.now(timezone.utc)`.

---

#### L-5 — Empty `app/api/` directory is dead code
| | |
|---|---|
| **Severity** | LOW |
| **Effort** | Trivial |
| **File** | [app/api/](app/api/) |

`app/api/` exists in the workspace but contains no files.  It creates confusion about the intended router layout and may cause import issues if auto-discovery is ever added.

**Fix:** Remove the empty directory, or add an `__init__.py` and a comment explaining the planned purpose.

---

#### L-6 — `safebrowsing.enabled: False` disables browser safe-browsing in Selenium
| | |
|---|---|
| **Severity** | LOW |
| **Effort** | Trivial |
| **File** | [app/core/netbank/getReport.py](app/core/netbank/getReport.py#L190) |

Edge's SafeBrowsing is explicitly disabled in the download preferences.  While this is typically done to avoid download prompts in headless mode, it also disables malware detection for any file downloaded via the browser.  The `# nosec B103` comment suppresses Bandit but the risk remains documented.

**Fix:** Leave `safebrowsing.enabled: False` but add an explicit code comment explaining why, and verify that downloaded XLS files are scanned by the `reportFormatter` pipeline before processing.

---

### Runability Checklist for TrueNAS (start here)

Quick checklist of the blockers that **prevent BAB from starting on a fresh TrueNAS deployment**:

- [ ] **[C-2]** Add `FIREBASE_API_KEY` to `truenas.env.example` and `docker-compose.truenas.yml`
- [ ] **[C-1]** Remove `.env` from git tracking; add `.env` to `.gitignore`
- [ ] **[H-1]** Read `SELENIUM_REMOTE_URL` from env in `getReport.py` instead of hardcoding
- [ ] **[M-7]** Add `user: "0:0"` to `docker-compose.truenas.yml` so `PUID`/`PGID` remapping works
- [ ] **[C-3]** Lock to `--workers 1` in Dockerfile CMD (in-memory token state is not multi-process safe)
- [ ] **[L-3]** Document `APP_UNREGISTER_DELETION_DAYS` in `truenas.env.example`

---

### Local Debugging Checklist (Linux & Windows)

- `PYTEST_RUNNING=1` or `UNIT_TEST=1` skips Firebase and scheduler initialization for fast unit tests.
- Set `SELENIUM_REMOTE_URL=http://localhost:4444` when running a local Selenium Grid.
- Set `LOG_LEVEL=DEBUG` and `LOG_JSON=false` for human-readable debug output.
- Use `docker compose -f docker/docker-compose.yml up` for a local dev stack (includes Selenium).
- On Windows, `fcntl` is unavailable — the scheduler automatically falls back to lock-free mode (one leader assumed). This is safe for single-process dev runs.
- Firebase test mode is activated by any of `PYTEST_CURRENT_TEST`, `PYTEST_RUNNING`, or `UNIT_TEST`.