---
description: "Change BAB runtime integration safely across Firebase, Firestore, scheduler, Docker, scripts, and TrueNAS-sensitive configuration."
---

# Runtime Integration - BAB

## Parameters

- change_goal: `{{ change_goal }}`
- touched_surface: `{{ touched_surface }}`
- runtime_constraints: `{{ runtime_constraints }}`

## Workflow

1. Inspect the owning integration code and the startup path that consumes it.
2. Identify Windows, Linux, Docker, and TrueNAS portability assumptions.
3. Apply the smallest change that preserves current behavior.
4. Run focused validation, such as a scheduler test, startup test, or targeted pytest module.
5. Update README or docs if the runtime contract changed.

## Rules

- Do not bury deployment changes inside unrelated refactors.
- Treat scheduler and filesystem behavior as multi-process sensitive.
- Document any new environment variables or path assumptions.
