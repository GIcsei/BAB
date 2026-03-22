# Security Audit – Git History

> **Date:** 2026-03-22
> **Scope:** Full commit history of `GIcsei/BAB`

## Critical Findings

### 1. Firebase Service-Account Private Key Committed

| Field | Value |
|---|---|
| **File** | `app/REDACTED_CREDENTIAL_FILE.json` |
| **Content** | Full GCP service-account JSON including RSA private key |
| **Introduced in** | `222c4c9` (Initial commit) |
| **Re-introduced in** | `fc53412` ("SECURITY VULNERABILITY" commit) |
| **Removed in** | `d2072e3`, `dd298f6` |

**Impact:** Anyone with read access to the repository can extract the
private key and impersonate the `REDACTED_SERVICE_ACCOUNT_EMAIL`
service account.

### 2. Firebase API Key Hardcoded in Source

| Field | Value |
|---|---|
| **Key** | `REDACTED_FIREBASE_API_KEY` |
| **Introduced in** | `95bf8a4` (`app/services/login_service.py`), `fc53412` (`QueryHandler.py`) |
| **Removed in** | `0fa7c8c`, `c2ff966` |

**Impact:** The API key was embedded in plaintext. While Firebase API keys
are often restricted by project settings, exposure broadens the attack
surface (quota abuse, phishing via the project identity).

### 3. `.env` File Tracked in Repository

| Field | Value |
|---|---|
| **File** | `.env` |
| **Content** | Deployment-specific host paths, user IDs, container config |
| **Introduced in** | `187ad46` |

**Impact:** Leaks internal directory structure and operator username
(`REDACTED_PATH`). While no secrets (passwords/keys) are stored directly,
the information aids targeted attacks.

## Required Actions

### Immediate (must be completed before next release)

1. **Rotate the Firebase service-account key.**
   Go to the GCP Console → IAM → Service Accounts →
   `REDACTED_SERVICE_ACCOUNT_EMAIL` →
   Keys → delete key ID `ebd117266a99…` and create a new one.

2. **Restrict or regenerate the Firebase API key.**
   GCP Console → APIs & Services → Credentials → restrict the key to
   your production domains/IPs, or generate a new one.

3. **Purge secrets from git history.**
   Use [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/) or
   `git filter-repo` to remove:
   - `app/REDACTED_CREDENTIAL_FILE.json`
   - All occurrences of `REDACTED_FIREBASE_API_KEY`
   - All occurrences of the private key blob

   After purging, force-push all branches and have every contributor
   re-clone. GitHub may still cache objects; open a support ticket to
   request garbage collection on the remote.

### Completed in This PR

- `.env` removed from git tracking and added to `.gitignore`.
- `.env.example` created with sanitized placeholder values.
- `.gitignore` hardened to prevent future commits of credential files
  (`*.json` service accounts, `*.pem`, `*.key`, `*.p12`, `*.pfx`,
  `auth_token*.json`, `master.json`).
