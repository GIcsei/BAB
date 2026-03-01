---
applyTo: "app/infrastructure/**/*.py,app/core/**/*.py"
---

Firebase access must:

- Be encapsulated in infrastructure layer.
- Not leak implementation details.
- Not rely on global state if avoidable.
- Avoid silent exception swallowing.
- Fail explicitly on auth verification errors.
- Avoid returning None on critical failures without logging.

Do not duplicate path resolution logic.
Do not hardcode collection names inside services.