# Security Audit – Git History

> **Date:** 2026-03-22
> **Scope:** Full commit history of `GIcsei/BAB`

## Critical Findings

### 1. Firebase Service-Account Private Key Committed

A full GCP service-account JSON file (including the RSA private key) was
committed to the repository. It was introduced in the initial commit and
re-introduced in a later commit titled "SECURITY VULNERABILITY".

**Impact:** Anyone with read access to the repository could extract the
private key and impersonate the associated service account.

### 2. Firebase API Key Hardcoded in Source

A Firebase Web API key was hardcoded in `app/services/login_service.py`
and `app/core/firestore_handler/QueryHandler.py`.

**Impact:** The API key was embedded in plaintext. While Firebase API keys
are often restricted by project settings, exposure broadens the attack
surface (quota abuse, phishing via the project identity).

### 3. `.env` File Tracked in Repository

The `.env` file was tracked in git, leaking deployment-specific host paths,
operator usernames, and container configuration.

**Impact:** Leaks internal directory structure and operator identity.
While no secrets (passwords/keys) were stored directly, the information
aids targeted attacks.

### 4. Hardcoded Credentials in Source

A personal email address and placeholder password were hardcoded in the
`QueryHandler.py` `__main__` block.

## Required Actions

### Immediate (must be completed before next release)

1. **Rotate the Firebase service-account key.**
   Go to the GCP Console → IAM → Service Accounts →
   delete the compromised key and create a new one.

2. **Restrict or regenerate the Firebase API key.**
   GCP Console → APIs & Services → Credentials → restrict the key to
   your production domains/IPs, or generate a new one.

3. **Purge secrets from git history.**
   Run the provided `filter-secrets.sh` script (uses `git-filter-repo`
   with `replacements.txt`):
   ```bash
   git clone https://github.com/GIcsei/BAB.git BAB-clean
   cd BAB-clean
   bash filter-secrets.sh
   git remote add origin https://github.com/GIcsei/BAB.git
   git push --force --all origin
   git push --force --tags origin
   ```
   Then have every contributor delete their old clone and re-clone.
   Open a GitHub support ticket to request server-side GC of
   unreachable objects.

### Completed in This PR

- `.env` removed from git tracking and added to `.gitignore`.
- `.env.example` created with sanitized placeholder values.
- `.gitignore` hardened to prevent future commits of credential files
  (`*.json` service accounts, `*.pem`, `*.key`, `*.p12`, `*.pfx`,
  `auth_token*.json`, `master.json`).
- `replacements.txt` created listing all sensitive strings for `git-filter-repo`.
- `filter-secrets.sh` script created to automate the history purge.
