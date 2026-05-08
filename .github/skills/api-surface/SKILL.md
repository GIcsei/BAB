# SKILL: API Surface - Routers, Schemas, OpenAPI, and Endpoint Documentation

## Purpose

Use this skill when changing FastAPI routers, request/response schemas, response models, endpoint docs, or contract validation for BAB.

## References

- Base backend URL: `https://bab.icsei.duckdns.org`
- Swagger UI: `https://bab.icsei.duckdns.org/docs`
- OpenAPI JSON: `https://bab.icsei.duckdns.org/openapi.json`

## Owned Files

- `app/routers/`
- `app/schemas/`
- API-facing parts of `app/main.py`
- `docs/api.md`
- README endpoint sections

## Working Rules

1. Inspect the router and its service together before changing a contract.
2. Treat the live OpenAPI document as evidence, not as a substitute for code inspection.
3. Keep routers thin: validation, dependency injection, service call, response mapping.
4. Prefer explicit response models and status codes.
5. When a route change affects docs, update docs after code and tests agree.

## Typical Checks

- Focused functional router tests under `tests/functionaltest/`
- Startup or main wiring tests when route registration changes
- Manual contract comparison against `/docs` or `/openapi.json` when drift is suspected
