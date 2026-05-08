# PROMPT INDEX

Use these prompt templates when a request matches a recurring backend workflow and a narrower prompt will reduce context.

## Current Prompt Map

| Request Shape | Prompt |
| --- | --- |
| Investigate and fix a backend defect | bug-fix.prompt.md |
| Add or refactor a backend service slice | new-service.prompt.md |
| Add or extend a FastAPI router slice | new-router.prompt.md |
| Reconcile endpoint contracts, schemas, or API docs | contract-sync.prompt.md |
| Change runtime integration, scheduler, or ops-sensitive behavior | runtime-integration.prompt.md |
| Change a schema with compatibility or persistence concerns | schema-migration.prompt.md |

## Usage Rules

- Start with `scrum-master` for multi-step or cross-layer work.
- Prefer these prompts when they make the request smaller and more repeatable.
- Do not use a prompt if it widens the task beyond the current owned slice.
