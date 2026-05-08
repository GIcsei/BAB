# SKILL: Storage and Persistence - Firestore, Filesystem State, and User Data Safety

## Purpose

Use this skill when changing Firestore handlers, filesystem-backed user state, credential files, or data loading boundaries in BAB.

## Primary Files

- `app/core/firestore_handler/`
- `app/infrastructure/firebase/`
- `app/services/data_service.py`
- `app/services/login_service.py`
- `app/services/user_deletion_service.py`
- `app/core/config.py`

## Persistence Rules

- Keep user data paths scoped and validated.
- Avoid duplicating path-resolution logic.
- Prefer explicit failures over silent partial writes.
- Treat credential files, token files, and pickled data as security-sensitive.
- Keep Firestore access encapsulated behind its handlers or adapters.

## Typical Checks

- Unit tests covering file path validation and storage behavior
- Integration tests for Firestore handler behavior
- Targeted review of atomicity, cleanup, and per-user isolation
