# Security Scanning Policy for BAB CI/CD

**Locked By:** Security-Engineer  
**Date:** 2026-05-14

## Decision Summary

### Q1: Scanning Tool Placement → Double-Pass Approach

| Tool | ci.yml | docker.yml | release.yml | Purpose |
|------|--------|-----------|-----------|---------|
| pip-audit | ✅ test job | — | ✅ re-check | Dependency vulnerabilities |
| bandit | ✅ test job | — | ✅ re-check | Code security issues |
| Trivy | — | ✅ on main push | ✅ before tag | OS/library vulnerabilities |

**Rationale:** Catches main-to-release drift; aligns with manual tag release process.

---

### Q2: Result Publication → GitHub Pages Reports (Option A1)

**Publication Strategy:**
- All jobs (ci, docker, release) upload scan results as JSON artifacts
- pages.yml extended to generate HTML reports
- Report location: `https://gicsei.github.io/BAB/reports/security/`
- Report structure: `/reports/security/[latest|vX.Y.Z]/[pip-audit|bandit|trivy].html`
- History kept: One report per tag + "latest" symlink

**Rationale:** Public audit trail, compliance tracking, historical visibility.

---

### Q3: Failure Thresholds and Exit Codes

**Trivy (Docker image scanning):**
- Exit code 1 on CRITICAL (blocks build)
- Exit code 0 on HIGH (warns, annotates, does not block)
- Format output: JSON (for pages) + table (for logs)

**Bandit (Code security analysis):**
- Exit code 1 on MEDIUM/CRITICAL (blocks build)
- Exit code 0 on LOW (reports only, does not block)
- Always output JSON for archival

**pip-audit (Dependency vulnerabilities):**
- Exit code 1 on any vulnerability found (blocks build)
- Exception: Autofix mode (see Decision #1) attempts upgrade, retests; if tests pass, continues

---

## Acceptance Criteria

- [ ] Trivy format changed from table to JSON in docker.yml
- [ ] ci.yml test job runs pip-audit + bandit before test results uploaded
- [ ] release.yml re-runs pip-audit + bandit + Trivy with exit codes as above
- [ ] All jobs upload JSON artifacts to `artifacts/security/`
- [ ] pages.yml extended: reads security JSON artifacts, generates HTML reports
- [ ] GitHub Pages deployed at `/reports/security/latest/` and `/reports/security/vX.Y.Z/`
- [ ] Documentation updated with scanning policy

