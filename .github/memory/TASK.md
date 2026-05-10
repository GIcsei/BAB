# ACTIVE TASK

- Task ID: BAB-RELEASE-STABILITY-PHASE4-2026-05-10
- Request: Implement Release Stability Sprint Phase 4 (T-10 / issue #4): fix release Docker and CI/CD workflow.
- Owner: platform-infrastructure
- Stage: done
- Priority: high
- Started: 2026-05-10

## Acceptance Criteria

- [x] Inspect release workflow gating and Docker publish ordering.
- [x] Implement minimal workflow hardening without contract drift.
- [x] Validate the workflow file syntax and release dependency shape.
- [x] Run targeted validation.
- [x] Sync required orchestration memory and backlog artifacts.

## Evidence

- Phase 4 platform-infrastructure implementation completed with release job gated behind Docker publish in `.github/workflows/release.yml`.
- Validation command passed: `python -c "from pathlib import Path; import yaml; data=yaml.safe_load(Path('.github/workflows/release.yml').read_text(encoding='utf-8')); assert data['jobs']['release']['needs']==['validate','docker']; print('YAML OK')"`.
- QA approved Phase 4 release gating.
