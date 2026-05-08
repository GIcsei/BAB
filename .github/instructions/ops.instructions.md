---
applyTo: "docker/**,scripts/**/*.sh,truenas.env.example"
---

Operations requirements:

- Preserve portability across Windows, Linux, Docker, and TrueNAS.
- Keep environment variable names stable unless the change is intentional and documented.
- Prefer explicit defaults and clear failure modes.
- Do not hardcode host-specific paths or secrets.
- Update setup docs when runtime configuration changes.
