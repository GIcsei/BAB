---
description: "Structured backend bug investigation and fix workflow for BAB with focused pytest verification and memory/TODO hygiene."
---

# Bug Fix Workflow - BAB

## Parameters

- bug_description: `{{ bug_description }}`
- affected_area: `{{ affected_area }}`
- reproduction_steps: `{{ reproduction_steps }}`
- expected_behavior: `{{ expected_behavior }}`
- actual_behavior: `{{ actual_behavior }}`
- todo_id: `{{ todo_id }}`

## Workflow

1. Reproduce or confirm the failure with the smallest relevant command.
2. Isolate the controlling code path and owning boundary.
3. Add or update a focused pytest when coverage is missing.
4. Apply the smallest fix that addresses the root cause.
5. Re-run the same focused validation before widening scope.
6. Record the result in memory and TODO surfaces if status changed.

## Rules

- Prefer minimal behavior-preserving changes.
- Avoid unrelated refactors.
- Keep router/service/core/infrastructure boundaries intact.
- Treat auth, credential, scheduler, and persistence bugs as high-signal routing cues.
