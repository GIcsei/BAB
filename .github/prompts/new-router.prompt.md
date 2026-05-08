---
description: "Scaffold or extend a FastAPI router in BAB with thin handlers, explicit schemas, service delegation, auth boundaries, and focused pytest coverage."
---

# New Router Slice - BAB

## Parameters

- router_file: `{{ router_file }}`
- endpoint_goal: `{{ endpoint_goal }}`
- auth_requirement: `{{ auth_requirement }}`
- request_models: `{{ request_models }}`
- response_models: `{{ response_models }}`

## Workflow

1. Confirm the owning service exists or define the missing service contract first.
2. Add or extend schema models before wiring the route.
3. Keep the router thin: parse, validate, delegate, map errors.
4. Verify auth dependency requirements explicitly.
5. Add or update focused functional tests for the new route behavior.

## Checklist

- [ ] Router delegates business logic to a service.
- [ ] Request and response models are explicit.
- [ ] Status codes and error mapping are intentional.
- [ ] Auth boundary is explicit.
- [ ] Focused tests cover success and a representative failure path.
