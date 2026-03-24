# Security Audit – Git History

> **Date:** 2026-03-22
> **Scope:** Full commit history of `GIcsei/BAB`
> **Last verified:** 2026-03-24 — all branches clean

## Critical Findings (all resolved)

### 1. Firebase Service-Account Private Key Committed ✅

A full GCP service-account JSON file (including the RSA private key) was
committed to the repository. It was introduced in the initial commit and
re-introduced in a later commit titled "SECURITY VULNERABILITY".

**Status:** Removed from all branches and purged from git history via
`git-filter-repo`. The credential JSON file no longer exists in any
git object.

### 2. Firebase API Key Hardcoded in Source ✅

A Firebase Web API key was hardcoded in `app/services/login_service.py`
and `app/core/firestore_handler/QueryHandler.py`.

**Status:** Replaced with `REDACTED_FIREBASE_API_KEY` across all history.

### 3. `.env` File Tracked in Repository ✅

The `.env` file was tracked in git, leaking deployment-specific host paths,
operator usernames, and container configuration.

**Status:** Operator paths replaced with generic placeholders (`/path/to/...`)
across all history. `.env` removed from tracking on this branch and added
to `.gitignore`.

### 4. Hardcoded Credentials in Source ✅

A personal email address and placeholder password were hardcoded in the
`QueryHandler.py` `__main__` block.

**Status:** Email and password replaced with `REDACTED_EMAIL` /
`REDACTED_PASSWORD` across all history.

## Remaining Actions

1. **Rotate the Firebase service-account key.**
   Go to the GCP Console → IAM → Service Accounts →
   delete the compromised key and create a new one.

2. **Restrict or regenerate the Firebase API key.**
   GCP Console → APIs & Services → Credentials → restrict the key to
   your production domains/IPs, or generate a new one.

3. **All contributors** should delete old clones and re-clone to avoid
   accidentally re-introducing purged objects.

4. Open a **GitHub support ticket** to request server-side garbage
   collection of unreachable objects.

## Completed

- `.env` removed from git tracking and added to `.gitignore`.
- `.env.example` created with sanitized placeholder values.
- `.gitignore` hardened to prevent future commits of credential files
  (`*.json` service accounts, `*.pem`, `*.key`, `*.p12`, `*.pfx`,
  `auth_token*.json`, `master.json`).
- `git-filter-repo` run with `--replace-text` and `--invert-paths` to
  purge all sensitive strings and the credential JSON file from history.
- Verified clean on all branches: `main`, `copilot/count-lines-of-code`,
  `copilot/remove-security-breach-commits`, `gh-pages`.
