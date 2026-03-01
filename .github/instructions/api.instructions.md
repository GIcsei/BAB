---
applyTo: "app/routers/**/*.py"
---

FastAPI requirements:

- Always use response models if defined.
- Use correct status codes.
- Validate request bodies strictly.
- Do not return raw dicts when models exist.
- Avoid broad exception catching.
- Map domain exceptions to HTTP exceptions clearly.

Routers must delegate to services.
Routers must not contain business logic.