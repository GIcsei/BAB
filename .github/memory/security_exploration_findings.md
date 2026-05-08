# Security Exploration Findings - BAB FastAPI Backend

## PRIORITIZED VULNERABILITIES & LOGIC BUGS

### CRITICAL SEVERITY

#### 1. **Legacy Token Fallback Bypass (Auth/Token Verification)**
- **Risk**: Authentication bypass via in-memory token registry
- **Location**: 
  - [app/core/auth.py](app/core/auth.py#L38-L49)
  - [app/application/services/token_service.py](app/application/services/token_service.py#L95-L99)
- **Issue**: After Firebase token verification fails, code falls back to `firebase.get_user_id_by_token(token)` which does a direct string comparison against stored tokens in `TokenRegistry.find_user_by_id_token()`. This is an exact match on `token.get("idToken")` in an in-memory dict.
- **Severity**: CRITICAL
- **Rationale**: 
  1. If an attacker can predict/guess a previously-seen token value, or if tokens are leaked, they can impersonate any user
  2. No expiration check on fallback tokens; stale tokens remain valid indefinitely
  3. Tokens are loaded at startup from disk (`credentials.json`) and kept in memory without rotation
- **Attack Vector**: Reuse or brute-force token strings; tokens could be extracted from logs, error responses, or crashes

#### 2. **No Rate Limiting or Brute-Force Protection**
- **Risk**: Brute-force attacks on login/registration, password reset email enumeration
- **Locations**:
  - [app/routers/login.py](app/routers/login.py#L49-L65) (register endpoint)
  - [app/routers/login.py](app/routers/login.py#L72-L87) (login endpoint)
  - [app/routers/login.py](app/routers/login.py#L229-L248) (password reset endpoint)
- **Issue**: No rate limiting, throttling, or backoff mechanisms detected in `pyproject.toml` or code
- **Severity**: CRITICAL
- **Rationale**: Attackers can brute-force valid email addresses and weak passwords without limit; password reset endpoint even admits it returns same message for valid/invalid emails but there's no timing protection

#### 3. **CORS Wildcard + Credentials = Credential Leakage**
- **Risk**: Any origin can make credentialed requests (XSS/CSRF from any site)
- **Location**: 
  - [app/main.py](app/main.py#L146-L150)
  - [app/core/config.py](app/core/config.py#L127-L133)
- **Issue**: `allow_origins` defaults to `["*"]` and `allow_credentials=True`. This violates CORS spec: browsers will reject responses when both are present unless Origin is explicitly whitelisted. This is a **configuration trap**—if admin sets even one explicit origin, the wildcard is removed and credentials work, opening CSRF vectors.
- **Severity**: CRITICAL
- **Rationale**: Wildcard + credentials contradicts spec. Even if browser enforcement exists, it's a dangerous default. Any frontend misconfig exposes credentialed APIs.

#### 4. **Token Verification Returns None in Test Mode, No Fallback Check**
- **Risk**: Test mode has no actual token verification; production behavior unpredictable
- **Location**: 
  - [app/infrastructure/firebase/auth.py](app/infrastructure/firebase/auth.py#L11-L33)
  - [app/core/auth.py](app/core/auth.py#L32-L38)
- **Issue**: `firebase.verify_id_token()` returns `None` silently if in test mode. Then `if verified and verified.get("user_id")` proceeds to fallback. Code assumes `verified` is a dict but it's `None`. This can silently bypass token checks if test env vars leak into prod.
- **Severity**: CRITICAL
- **Rationale**: Silent `None` return is a logic bomb. If `is_testing_env()` accidentally triggers in prod (via env var pollution), all token verification fails silently and falls back to in-memory lookup, opening bypass.

### HIGH SEVERITY

#### 5. **HTTPBearer Dependency Bypass (Missing Exception Handling)**
- **Risk**: If `creds` param is None, code does `.credentials` on None
- **Location**: [app/core/auth.py](app/core/auth.py#L23-L28)
- **Issue**: `token = creds.credentials if creds else None` assumes `creds` is an `HTTPAuthorizationCredentials` object or None. HTTPBearer raises 403 if header missing, but FastAPI dependency injection could theoretically pass None in edge cases (e.g., optional dependency misuse). The code handles it, but it's non-obvious and relies on FastAPI behavior.
- **Severity**: HIGH
- **Rationale**: While HTTPBearer should enforce 403, the defensive check suggests uncertainty. Relying on framework behavior for auth is risky.

#### 6. **Race Condition: File-Based Token Persistence vs In-Memory Registry**
- **Risk**: Token state inconsistency; possible session fixation or use-after-free
- **Locations**:
  - [app/application/services/token_service.py](app/application/services/token_service.py#L156-L220) (load_tokens_from_dir)
  - [app/services/login_service.py](app/services/login_service.py#L100-L125) (login writes credentials)
- **Issue**: Tokens are stored in `TokenRegistry` (in-memory, thread-safe with RLock) and also written to `credentials.json` (on disk). On startup, tokens are reloaded from disk. No atomic coordination: if a token is updated in memory but not yet written, a crash loses it. If disk token is stale and startup reloads it, user gets old token. Multiple processes (scheduler, API server) could write to same `credentials.json` without locking.
- **Severity**: HIGH
- **Rationale**: Concurrent file I/O without file-level locking (via `fcntl.flock` or similar) means race conditions in distributed deployments (TrueNAS multi-process).

#### 7. **Path Traversal via User-Controlled `user_id` in Regex (Insufficient)**
- **Risk**: While regex validation exists, it's not bulletproof
- **Location**: [app/routers/data_plot.py](app/routers/data_plot.py#L24-L32)
- **Issue**: `_validate_user_id()` uses regex `^[a-zA-Z0-9_\-\.]+$` and `_validate_file_path()` uses regex to check `.csv|.parquet|.json`. But regex alone doesn't prevent directory traversal. The actual validation `_validate_user_path()` in [app/services/data_service.py](app/services/data_service.py#L37-L41) uses `.resolve()` and checks if result is inside base dir. However, if symlinks exist in `base_dir`, a crafted path could escape.
- **Severity**: HIGH
- **Rationale**: Symlink attacks are possible if attacker can create symlinks inside the user data directory (e.g., via the scheduler or upload functionality not shown). Calling `.resolve()` is good but doesn't block TOCTOU (time-of-check-time-of-use).

#### 8. **Missing Input Validation on Query Parameters**
- **Risk**: DoS via huge file reads, column injection in Firestore queries
- **Location**: [app/routers/data_plot.py](app/routers/data_plot.py#L110-L150)
- **Issue**: `max_points` parameter defaults to 10000 and has `le=100000` limit. But the underlying data service loads entire dataframe first, then extracts series—no streaming. Large files could exhaust memory. Also, `y` and `x` column parameters are user input passed to `extract_series_async()` without further validation; if columns are used in Firestore queries (via `Query.py`), injection is possible.
- **Severity**: HIGH
- **Rationale**: Memory exhaustion is feasible; column name injection could lead to query abuse if Firestore queries are dynamic.

#### 9. **Credentials Stored in JSON on Disk Without Encryption (Fernet Present But Fallback Exists)**
- **Risk**: NetBank credentials are encrypted on disk but credentials.json (Firebase tokens) are NOT
- **Location**: 
  - [app/core/netbank/credentials.py](app/core/netbank/credentials.py) (good: uses Fernet)
  - [app/services/login_service.py](app/services/login_service.py#L45-L55) (bad: credentials.json is plain JSON)
- **Issue**: Firebase credentials (idToken, refreshToken, email, user_id) are written to `credentials.json` in plaintext with only OS-level permissions (0o600). Tokens are not encrypted. An attacker with file system access reads all tokens. Machine compromise → full account compromise.
- **Severity**: HIGH
- **Rationale**: Tokens should be encrypted at rest using the same Fernet approach as NetBank credentials. Failure to do so is a critical data exposure vector.

#### 10. **Exception Details Leaked in Error Responses (Partial)**
- **Risk**: Detailed error messages could expose internals
- **Location**: [app/core/error_mapping.py](app/core/error_mapping.py#L42-L56)
- **Issue**: `get_error_response()` returns a generic error for non-AppException but logs the exception. However, for AppException, the `message` field is directly returned to the client. If an exception message contains system paths, SQL queries, or internal details, it leaks. The code is better than returning full tracebacks, but still risky.
- **Severity**: HIGH
- **Rationale**: Error messages like "File not found: /var/app/user_data/user_123/file.csv" leak the directory structure to attackers.

### MEDIUM SEVERITY

#### 11. **Token Refresh on Startup Can Hang or Fail Silently**
- **Risk**: If token refresh is slow, app startup can be delayed; if it fails, fallback is untested
- **Location**: [app/main.py](app/main.py#L103-L120)
- **Issue**: Startup code tries to refresh all tokens. If network is slow/unavailable, it logs warning and falls back to `load_tokens_from_dir(..., refresh=False)`. But the fallback loads stale tokens, and there's no indication in health check that tokens are stale. App appears ready but tokens may be expired.
- **Severity**: MEDIUM
- **Rationale**: Could lead to runtime auth failures after what appears to be a successful startup. Health check doesn't differentiate between fresh and stale tokens.

#### 12. **Email Enumeration via Password Reset (Timing)**
- **Risk**: Attackers can enumerate valid emails
- **Location**: [app/routers/login.py](app/routers/login.py#L229-L248) and [app/services/login_service.py](app/services/login_service.py#L327-L335)
- **Issue**: Password reset endpoint calls `auth_client.send_password_reset_email(email)` which could succeed or fail depending on whether email exists. Code catches all exceptions and returns the same message to prevent enumeration. However, there's no timing attack mitigation—network latency could differ based on whether email lookup succeeds or fails internally.
- **Severity**: MEDIUM
- **Rationale**: Perfect protection requires constant-time responses; current implementation is good but not perfect.

#### 13. **Unregister/Deletion Has Race Condition & Incomplete Cleanup**
- **Risk**: User can access API after requesting unregister, or data not deleted
- **Location**: [app/services/login_service.py](app/services/login_service.py#L240-L300) and [app/routers/login.py](app/routers/login.py#L186-L197)
- **Issue**: Unregister marks user as blocked in Firestore (best-effort, non-fatal on failure) but doesn't immediately reject API calls. User is scheduled for deletion 60 days later. Between unregister and deletion, a sophisticated attacker could still use the API if they have a valid token (tokens aren't immediately revoked). Also, `_block_user_in_firestore()` is non-fatal, so if it fails, the block never happens and user stays active.
- **Severity**: MEDIUM
- **Rationale**: Soft-delete with delayed cleanup is risky; should immediately revoke tokens and block API access. Firestore failure silently allows continued access.

#### 14. **Missing HTTPS/TLS Enforcement**
- **Risk**: Credentials transmitted over HTTP
- **Location**: All endpoints (app/routers/, app/main.py)
- **Issue**: FastAPI config doesn't enforce TLS/HTTPS. If deployed behind a proxy without TLS termination, or if proxy strips HTTPS headers, tokens could be transmitted over HTTP. There's no `Strict-Transport-Security` header or scheme enforcement.
- **Severity**: MEDIUM
- **Rationale**: Deployment config should enforce it, but app-level enforcement is missing. Tokens could be intercepted in transit if deployment is misconfigured.

#### 15. **Logging Leaks Sensitive Data**
- **Risk**: Tokens, emails, user_ids logged to disk/stdout
- **Location**: Multiple endpoints log user_id, email, token operations
  - [app/routers/login.py](app/routers/login.py#L61-L62) logs email
  - [app/services/login_service.py](app/services/login_service.py#L70) logs email
  - [app/core/auth.py](app/core/auth.py#L36) logs verified dict (could include user_id)
- **Issue**: Debug/info logs contain PII. If logs are forwarded to 3rd party service, stored insecurely, or included in error reports, they leak user data.
- **Severity**: MEDIUM
- **Rationale**: Logs are often treated as "safe" but they're an attack surface. Credentials and emails should never be logged in production.

#### 16. **No Audit Trail for Sensitive Actions**
- **Risk**: Account takeover not detectable
- **Location**: No explicit audit logging
- **Issue**: No structured logging of sensitive actions (login, logout, unregister, credential changes, data access). If account is compromised, no way to detect or investigate unauthorized access.
- **Severity**: MEDIUM
- **Rationale**: Compliance and forensics require audit trails for sensitive operations.

### LOW SEVERITY / DESIGN CONCERNS

#### 17. **Serialize Error Could Leak Data via Detailed Error Messages**
- **Location**: [app/services/data_service.py](app/services/data_service.py#L84-L94)
- **Issue**: Deserialization errors include filename and reason in message. If reason contains internal error details, it's exposed to client.
- **Severity**: LOW
- **Rationale**: Already mitigated by exception_to_http mapping, but filename alone is somewhat sensitive.

#### 18. **No CSRF Token Validation**
- **Location**: All POST/PUT endpoints
- **Issue**: No CSRF token in requests; relies on SameSite cookie attribute. POST endpoints don't validate origin or custom headers.
- **Severity**: LOW
- **Rationale**: SameSite is modern mitigation; CSRF tokens are legacy. But combined with wildcard CORS + credentials, it's still a risk.

#### 19. **Password Minimum Requirements Not Enforced**
- **Location**: [app/routers/login.py](app/routers/login.py#L49-L65) (register)
- **Issue**: Firebase Auth likely has defaults, but no app-level validation of password strength
- **Severity**: LOW
- **Rationale**: Relies on Firebase; not a blocker but should document/enforce policy.

#### 20. **No Explicit Dependency Validation**
- **Risk**: Hidden dependencies could introduce vulnerabilities
- **Location**: [pyproject.toml](pyproject.toml)
- **Issue**: `sseclient>=0.0.27` is very permissive version constraint. No pinned versions. Allows automated updates that could break or introduce vulnerabilities.
- **Severity**: LOW
- **Rationale**: Best practice is to pin to tested versions.

---

## HOTSPOT FILE/FUNCTION REFERENCES FOR MANUAL INSPECTION

### MUST INSPECT:
1. [app/core/auth.py](app/core/auth.py) - Full file
   - Functions: `get_current_user_id()`, `get_current_user()`
   - Check: Legacy fallback logic, token verification flow

2. [app/application/services/token_service.py](app/application/services/token_service.py) - Full file
   - Functions: `TokenRegistry.find_user_by_id_token()`, `TokenService.load_tokens_from_dir()`
   - Check: In-memory token lookup, file I/O race conditions

3. [app/services/login_service.py](app/services/login_service.py) - Lines 40-125 (login), 240-300 (unregister)
   - Functions: `login_user()`, `register_user()`, `unregister_user()`
   - Check: Token persistence, deletion logic

4. [app/main.py](app/main.py) - Lines 146-150 (CORS), 103-120 (token refresh)
   - Check: CORS configuration, startup sequence

5. [app/routers/login.py](app/routers/login.py) - All POST endpoints
   - Functions: `register()`, `login()`, `password_reset()`
   - Check: Input validation, rate limiting

6. [app/routers/data_plot.py](app/routers/data_plot.py) - Lines 24-32 (validation), 110-150 (series extraction)
   - Functions: `_validate_user_id()`, `_validate_filename()`, `get_series()`
   - Check: Path traversal, parameter validation

### SHOULD INSPECT:
7. [app/core/netbank/credentials.py](app/core/netbank/credentials.py) - Full file
   - Check: Encryption logic, credential retrieval (compare with unencrypted Firebase tokens)

8. [app/infrastructure/firebase/auth.py](app/infrastructure/firebase/auth.py) - Full file
   - Function: `verify_id_token()`
   - Check: Test mode bypass, None return handling

9. [app/core/firestore_handler/QueryHandler.py](app/core/firestore_handler/QueryHandler.py) - Lines 93-97
   - Functions: `verify_id_token()`, `get_user_id_by_token()`
   - Check: Delegation to services

10. [app/core/error_mapping.py](app/core/error_mapping.py) - Full file
    - Check: Error detail sanitization

---

## UNKNOWNS & CLARIFICATIONS NEEDED

1. **Is Firebase Auth configured with strong token expiration?** (e.g., 1 hour)
   - If tokens live > 24 hours, legacy fallback becomes more dangerous

2. **Does the deployment enforce HTTPS/TLS at the load balancer?**
   - If not, tokens are sent over HTTP

3. **Are logs encrypted at rest and access-controlled?**
   - If logs contain PII and are public, it's a critical leak

4. **Is there any rate limiting at the reverse proxy level (e.g., nginx)?**
   - App-level rate limiting is missing; proxy might provide it

5. **Can users upload arbitrary files, or are they auto-generated by scheduler?**
   - If upload allowed, symlink attacks become feasible

6. **Is file system shared across multiple app instances, or isolated?**
   - Affects severity of race conditions

7. **What is the Firebase project's IAM/security rules configuration?**
   - Does Firestore require authentication? Could an unauthenticated user bypass auth layer?

8. **How are credentials.json files backed up/restored?**
   - Could lead to token replay attacks if old credentials are restored

9. **Is there automated security scanning (bandit, pip-audit, etc.) in CI/CD?**
   - Would catch some of these issues

10. **What is the incident response procedure for token compromise?**
    - How quickly can tokens be revoked globally?

---

## SUMMARY TABLE

| ID | Category | Severity | Function/File | Issue | Fix Priority |
|---|---|---|---|---|---|
| 1 | Auth | CRITICAL | auth.py#38-49 | Legacy token fallback enables bypass | 1 (remove fallback or strict expiry) |
| 2 | Auth | CRITICAL | login.py | No rate limiting | 2 (add SlowAPI or similar) |
| 3 | CORS | CRITICAL | main.py#146-150 | Wildcard + credentials | 3 (set explicit origins) |
| 4 | Auth | CRITICAL | firebase/auth.py#11-33 | Silent None return on test mode | 4 (raise error instead) |
| 5 | Auth | HIGH | auth.py#23-28 | HTTPBearer bypass risk | 5 (document assumption) |
| 6 | Concurrency | HIGH | token_service.py#156-220 | File race conditions | 6 (add file locking) |
| 7 | Input Validation | HIGH | data_plot.py#24-32 | Path traversal symlink risk | 7 (block symlinks or check permissions) |
| 8 | Input Validation | HIGH | data_plot.py#110-150 | Missing column validation for queries | 8 (validate column names) |
| 9 | Data Protection | HIGH | login_service.py#45-55 | Unencrypted credentials.json | 9 (encrypt with Fernet) |
| 10 | Error Handling | HIGH | error_mapping.py#42-56 | Exception details leaked | 10 (sanitize messages) |
| 11 | Startup | MEDIUM | main.py#103-120 | Token refresh hang/silent failure | 11 (timeout + explicit status) |
| 12 | Auth | MEDIUM | login.py#229-248 | Email enumeration via timing | 12 (constant-time response) |
| 13 | Lifecycle | MEDIUM | login_service.py#240-300 | Incomplete user blocking on unregister | 13 (immediate token revocation) |
| 14 | Transport | MEDIUM | all | No HTTPS enforcement | 14 (deploy-time or app middleware) |
| 15 | Logging | MEDIUM | login.py, auth.py | PII in logs | 15 (redact sensitive fields) |
| 16 | Audit | MEDIUM | all | No audit trail | 16 (structured audit logging) |
| 17 | Error Handling | LOW | data_service.py#84-94 | Filename exposure in error | 17 (generic error messages) |
| 18 | CSRF | LOW | all | No CSRF tokens | 18 (document SameSite reliance) |
| 19 | Password | LOW | login.py#49-65 | No password policy | 19 (enforce via Firebase) |
| 20 | Dependencies | LOW | pyproject.toml | Loose version constraints | 20 (pin versions) |
