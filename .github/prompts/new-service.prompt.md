---
description: "Scaffold or refactor a BAB service slice in app/services or app/application/services with clear boundaries, error handling, and focused pytest coverage."
---

# New Service Slice - BAB

## Parameters

- service_file: `{{ service_file }}`
- service_goal: `{{ service_goal }}`
- dependencies: `{{ dependencies }}`
- primary_inputs: `{{ primary_inputs }}`
- primary_outputs: `{{ primary_outputs }}`

## Workflow

1. Confirm the owning boundary: service, application service, or infrastructure.
2. Keep orchestration and business rules in the service layer.
3. Reuse existing exceptions, config, and auth helpers where possible.
4. Add focused unit tests for the new or changed behavior.
5. Validate the service through the narrowest relevant pytest target.

## Checklist

- [ ] Logic stays out of routers.
- [ ] Dependencies are explicit and reusable.
- [ ] Exceptions map cleanly to upstream callers.
- [ ] Security-sensitive or persistence-sensitive behavior is not duplicated.
- [ ] Focused pytest coverage exists for the new branch or behavior.
