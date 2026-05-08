---
description: "Guide BAB schema or persistence shape changes with backward-compatibility checks, propagation, and focused verification."
---

# Schema Migration - BAB

## Parameters

- schema_name: `{{ schema_name }}`
- change_type: `{{ change_type }}`
- change_description: `{{ change_description }}`
- affected_storage: `{{ affected_storage }}`
- backward_compatible: `{{ backward_compatible }}`

## Workflow

1. Identify whether the change affects request schemas, response schemas, persisted files, or Firestore documents.
2. Inspect all read and write paths for that shape.
3. Preserve compatibility where required, or document the intentional break.
4. Update tests that cover both old and new expectations when needed.
5. Validate with the smallest meaningful pytest slice.

## Rules

- Do not change persistence shape in one location only.
- Update docs when operators or users must adapt.
- Treat path validation, cleanup, and user isolation as part of the schema impact.
