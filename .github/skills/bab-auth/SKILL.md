# SKILL: BAB Authentication - Token Verification, Credential Lifecycle, and Sensitive Boundaries

## Purpose

Use this skill when changing or reviewing authentication, token handling, credential persistence, secret exposure, or auth-sensitive request boundaries in BAB.

## Primary Files

- `app/core/auth.py`
- `app/infrastructure/firebase/auth.py`
- `app/application/services/token_service.py`
- `app/services/login_service.py`
- `app/routers/login.py`
- `app/routers/netbank_credentials.py`

## Auth Model

1. Requests reach FastAPI routes.
2. Auth dependencies verify the caller and derive `user_id`.
3. Firebase-backed verification is the primary trust boundary.
4. Token persistence and credential lifecycle live in service/application layers.
5. Sensitive outputs must be redacted from logs and error responses.

## Review Rules

- Never log tokens, passwords, or secret-bearing payloads.
- Preserve explicit auth checks at the route boundary.
- Prefer fail-closed behavior when auth verification is uncertain.
- Re-check user isolation when filesystem or Firestore lookups use `user_id`.
- When auth behavior changes, pair code review with focused tests.

## Typical Checks

- `pytest tests/unittest/test_auth.py -q`
- `pytest tests/functionaltest/test_login_router.py -q`
- Focused credential or login service tests under `tests/unittest/`
