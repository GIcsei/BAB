---
applyTo: "tests/**/*.py"
---

Testing requirements:

- Maintain existing coverage.
- Update tests if logic changes.
- Avoid rewriting stable tests.
- Ensure deterministic behavior.
- Avoid reliance on global state between tests.
- Mock infrastructure boundaries only.
- Prefer focused `pytest` targets before broad suite runs.
- Keep fixtures small and scoped to the behavior under test.

If a change introduces new edge cases, add corresponding tests.