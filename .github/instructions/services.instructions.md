---
applyTo: "app/services/**/*.py,app/application/services/**/*.py"
---

Service requirements:

- Keep business logic in services, not routers.
- Prefer small, explicit helper functions over deeply nested branches.
- Propagate cancellation or timeout context when the surrounding design already supports it.
- Avoid duplicating auth, path, or persistence checks across multiple services.
- Raise domain-specific exceptions instead of transport-shaped errors.

Services must remain readable, testable, and transport-agnostic.
