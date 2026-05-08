---
description: "Sync BAB endpoint contracts, schemas, and API docs with verified FastAPI behavior and the live OpenAPI surface."
---

# Contract Sync - BAB

## Parameters

- target_surface: `{{ target_surface }}`
- reason: `{{ reason }}`
- impacted_files: `{{ impacted_files }}`

## Workflow

1. Inspect the owning router, schema, and service files.
2. Compare behavior against `https://bab.icsei.duckdns.org/docs` or `/openapi.json` when live contract evidence matters.
3. Fix drift in request models, response models, status codes, or docs.
4. Run the smallest relevant pytest or API-focused check.
5. Update docs only after behavior and validation align.

## Rules

- Preserve backward compatibility unless the request explicitly allows contract changes.
- Do not hide behavior mismatches behind documentation edits.
- Keep routers transport-only and delegate logic to services.
