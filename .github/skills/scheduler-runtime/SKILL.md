# SKILL: Scheduler Runtime - Startup, Restore, Multi-Worker Safety, and Portability

## Purpose

Use this skill when changing scheduler behavior, startup/restore paths, runtime coordination, or environment-sensitive integration for BAB.

## Primary Files

- `app/services/scheduler.py`
- `app/infrastructure/sched/scheduler.py`
- `app/main.py`
- `docker/entrypoint.sh`
- `docker/`
- `scripts/`

## Runtime Concerns

- Startup and restore order must stay deterministic.
- Scheduler execution must tolerate multi-worker deployment.
- File locking or coordination behavior must be explicit.
- Windows, Linux, Docker, and TrueNAS assumptions must remain valid.

## Working Rules

1. Inspect startup/lifespan code together with scheduler internals.
2. Treat path handling, file locking, and environment variable usage as runtime contracts.
3. Separate operational changes from business logic changes.
4. Update docs when runtime setup or behavior changes.

## Typical Checks

- Focused scheduler tests under `tests/unittest/`
- Startup-oriented tests under `tests/functionaltest/`
- Targeted validation of Docker or script changes when touched
