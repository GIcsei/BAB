---
applyTo: "app/routers/**/*.py"
---

FastAPI router requirements:

- Keep handlers thin: parse, validate, delegate, map errors.
- Use explicit response models when models exist.
- Use intentional status codes and auth dependencies.
- Avoid broad exception catching inside routers.
- Map domain exceptions to HTTP behavior clearly and consistently.
- Keep request validation close to the route boundary.

Routers must delegate to services and must not contain business logic.