---
applyTo: "app/**/*.py"
---

The project follows a strict service-based architecture.

Enforce:
- Routers must remain thin.
- Business logic belongs in services.
- Infrastructure access must be abstracted.
- No Firebase calls in routers.
- No circular dependencies.
- Respect layer separation:
  routers/
  services/
  core/
  infrastructure/
  models/

Refactor to reduce duplication, nesting, and unclear naming.

Never mix transport and domain logic.
Never introduce global mutable shared state.

excludeAgent: "code-review"