# BAB Test Coverage Analysis

## High-Risk Untested/Undertested Areas

### 1. CRITICAL: Lifespan/Startup Error Handling (SEVERITY: HIGH - App Won't Start)
**Production Files:**
- [app/main.py](app/main.py#L44-L128) - lifespan() context manager
- Lines: Startup exception handling when services fail

**Gap:**
- No test for startup exception raising when initialize_firebase_admin() fails with fatal error
- No test for get_credential() returning None (should fail startup)
- No test when scheduler or deletion worker fail to start
- No test for exception during stop_scheduler_on_shutdown

**Impact:** If Firebase init fails, app may silently start in degraded state instead of failing fast

**Tests:** Only happy paths tested in test_main_startup.py

---

### 2. CRITICAL: CORS Configuration Bypass (SEVERITY: HIGH - XSS/Data Breach)
**Production Files:**
- [app/main.py](app/main.py#L146-L153) - CORS middleware configuration

**Gap:**
- CORS_ALLOWED_ORIGINS from env directly without validation
- No test for empty/None CORS origins (wildcard behavior)
- No test for malicious origins in CSV list
- No test for origin validation bypass via nested/special chars

**Impact:** Misconfiguration could expose all endpoints to unauthorized origins

**Tests:** test_cors.py only tests basic happy path

---

### 3. CRITICAL: Scheduler Leadership Race Condition (SEVERITY: CRITICAL - Data Loss)
**Production Files:**
- [app/infrastructure/sched/scheduler.py](app/infrastructure/sched/scheduler.py#L223-L275) - Leadership election
- Lines: _try_acquire_leadership, _release_leadership, _leader_loop

**Gap:**
- No test for concurrent leadership attempts from multiple processes
- No test for file lock contention
- No test for fcntl lock timeout/exceptions
- No test for leadership transitions (acquire -> release -> reacquire)
- No test for zombie lock file cleanup
- No test for platform without fcntl (Windows path tested, but edge cases not)

**Impact:** Multiple scheduler instances could run jobs simultaneously, causing duplicate data, file corruption, or missed jobs

**Tests:** test_scheduler.py doesn't test concurrent scenarios

---

### 4. CRITICAL: Token Verification Fallback Chain (SEVERITY: HIGH - Auth Bypass)
**Production Files:**
- [app/core/auth.py](app/core/auth.py#L23-L55) - get_current_user_id()
- [app/infrastructure/firebase/auth.py](app/infrastructure/firebase/auth.py#L10-L32) - verify_id_token()

**Gap:**
- No test for when verify_id_token returns empty dict (should fail, not fallback)
- No test for malformed token that causes firebase-admin to raise specific exception
- No test for token with valid structure but wrong user_id field
- No test for get_user_id_by_token() returning stale token
- No test for concurrent token verification with stale cache

**Impact:** Attacker with old token could bypass auth if legacy token still in registry

**Tests:** test_auth.py covers only basic cases, not edge cases

---

### 5. HIGH: Credential Encryption Key Failures (SEVERITY: HIGH - Plaintext Credentials)
**Production Files:**
- [app/core/netbank/credentials.py](app/core/netbank/credentials.py#L50-L95) - _ensure_key()

**Gap:**
- No test for NETBANK_MASTER_KEY being invalid (bad length, not base64)
- No test for key file corruption (file exists but unreadable)
- No test for key file permissions not being restrictive
- No test for os.open() failure during key write
- No test for race condition during concurrent key generation

**Impact:** If key fails silently, credentials stored in plaintext

**Tests:** test_credentials*.py has coverage but missing corruption/concurrency scenarios

---

### 6. CRITICAL: Scheduler Job Stalling (SEVERITY: CRITICAL - Service Hangs)
**Production Files:**
- [app/infrastructure/sched/scheduler.py](app/infrastructure/sched/scheduler.py#L334-L388) - _worker_loop()

**Gap:**
- No test for job hanging indefinitely (_Job._perform_task never returns)
- No test for worker thread becoming unresponsive (threading deadlock)
- No test for heap corruption under concurrent modifications
- No test for condition variable spurious wakeups
- No test for long-running jobs blocking shutdown

**Impact:** Scheduler worker could hang, blocking app shutdown or consuming resources

**Tests:** test_scheduler_worker.py doesn't test threading edge cases

---

### 7. HIGH: File Path Traversal in Data Service (SEVERITY: CRITICAL - Arbitrary File Access)
**Production Files:**
- [app/services/data_service.py](app/services/data_service.py#L33-L48) - _validate_user_path()
- Lines: symlink detection, path.resolve() comparison

**Gap:**
- No test for symlink pointing to sibling user directory
- No test for symlink pointing outside base_dir (created after validation)
- No test for race condition: validate then symlink created before access
- No test for case sensitivity bypass on case-insensitive filesystems

**Impact:** User could access other users' files via crafted symlinks

**Tests:** test_security_hardening.py tests current symlinks, not race conditions

---

### 8. HIGH: Error Response Information Leakage (SEVERITY: MEDIUM - Information Disclosure)
**Production Files:**
- [app/core/error_mapping.py](app/core/error_mapping.py#L42-L56) - get_error_response()
- [app/main.py](app/main.py#L155-L175) - error_handling_middleware()

**Gap:**
- No test for internal exception details leaked in 500 responses
- No test for stack traces exposed in development mode
- No test for sensitive data (paths, SQL, credentials) in error messages

**Impact:** Attacker could glean system info from error messages

**Tests:** No error response content validation tests

---

### 9. CRITICAL: Netbank Selenium Timeout/Hang (SEVERITY: CRITICAL - Resource Leak)
**Production Files:**
- [app/core/netbank/getReport.py](app/core/netbank/getReport.py#L100-150) - ErsteNetBroker class
- Lines: Selenium webdriver initialization, timeouts

**Gap:**
- No test for Selenium hanging without timeout
- No test for webdriver process not terminating
- No test for memory leak from unclosed browsers
- No test for concurrent Selenium instances per user
- No test for invalid credentials causing infinite loop

**Impact:** Hung Selenium instances could exhaust server resources

**Tests:** No Netbank tests (Selenium tests likely integration-only)

---

### 10. HIGH: Deletion Worker Race Condition (SEVERITY: HIGH - Data Corruption)
**Production Files:**
- [app/services/user_deletion_service.py](app/services/user_deletion_service.py#L74-L120) - execute_expired_deletions()

**Gap:**
- No test for concurrent deletion attempts (DeletionWorker vs manual call)
- No test for shutil.rmtree() failing mid-way (partial deletion)
- No test for deletion_pending.json being modified during deletion
- No test for directory locked by scheduler job

**Impact:** User data could be partially deleted, leaving corrupt state

**Tests:** test_user_deletion_service.py has rmtree failure test but not concurrency

---

### 11. MEDIUM: Firestore Request Validation (SEVERITY: MEDIUM - Data Injection)
**Production Files:**
- [app/core/firestore_handler/DatabaseHandler.py](app/core/firestore_handler/DatabaseHandler.py#L105-L132) - _request()
- [app/core/firestore_handler/FirestoreService.py](app/core/firestore_handler/FirestoreService.py#L70-100) - HTTP requests

**Gap:**
- No test for SQL injection via query parameters
- No test for XXE in XML responses
- No test for HTTP response injection
- No test for timeout handling on slow Firestore responses

**Impact:** Malformed Firestore responses could cause crashes or data corruption

**Tests:** Integration tests exist but not for malicious responses

---

### 12. HIGH: User Deletion Service Metadata Corruption (SEVERITY: HIGH - State Corruption)
**Production Files:**
- [app/services/user_deletion_service.py](app/services/user_deletion_service.py#L18-45) - schedule_user_deletion(), cancel_user_deletion()

**Gap:**
- No test for deletion_pending.json being invalid JSON
- No test for missing deletion_at_ms field
- No test for negative timestamps
- No test for deletion_at_ms in past (immediate deletion)

**Impact:** Corrupted metadata could cause immediate deletion or leaked scheduling

**Tests:** test_user_deletion_service.py doesn't test malformed metadata

---

## Summary of Gaps

### By Risk Level:
- **CRITICAL (9)**: Scheduler leadership, job stalling, token bypass, path traversal, lifespan errors, Netbank timeouts, deletion race, CORS bypass, startup failures
- **HIGH (11)**: Credential key failures, error leakage, deletion metadata, Firestore injection

### Test Categories Missing:
1. **Concurrency/Threading**: Race conditions, deadlocks, concurrent access
2. **Error Conditions**: Corruption, malformed input, timeout scenarios
3. **Security**: Path traversal race conditions, auth bypass edge cases, CORS config
4. **Resource Cleanup**: Hanging processes, file descriptors, thread leaks
5. **Configuration Validation**: Invalid env vars, missing credentials

### Effort Estimate: 80-120 hours
- Concurrency tests: 30-40h
- Error handling: 20-30h
- Security: 15-20h
- Netbank/Selenium: 15-20h (requires integration setup)
