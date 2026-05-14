# CI/CD Refactor: Accepted Policies & Implementation Plan

**Session Date:** 2026-05-14  
**Issue:** Release and Docker.yml duplicate work; pip-audit detects vulns but no fix strategy; GitHub Pages doesn't publish reports  
**Ownership:** Tech-lead, Security-Engineer, Platform-Infrastructure, Tester, Documentation-Writer

---

## ACCEPTED DECISIONS

### Decision #1: pip-audit Vulnerability Handling (Option B: Autofix with Validation)

**Policy:**
- pip-audit runs in **main CI** (not just release)
- Detected vulnerability → auto-attempt `pip install --upgrade {package}`
- Re-run full test suite (70% coverage gate must pass)
- If tests pass → commit uv.lock + bump pyproject.toml version → pass workflow
- If tests fail → **block release**, notify developer for manual intervention
- MAJOR version bumps stay manual (not auto-fixed)

**Acceptance Criteria:**
- ✅ Build status clear in GitHub UI
- ✅ Autofix only for PATCH updates
- ✅ Test validation gate required

---

### Decision #2: Version Bump and Release Process (Manual Tag from Pre-Bumped)

**Process:**
1. Developer bumps version in pyproject.toml
2. Commit to main
3. Create annotated git tag `v{version}` pointing to that commit
4. Push branch + tag
5. CI detects tag → runs release.yml

**Validation Required:**
- Extract version from pyproject.toml
- Extract version from git tag (remove `v` prefix)
- Compare; **fail release if mismatch** (prevents tag/code skew)
- Release runs **only from main branch**

**Acceptance Criteria:**
- ✅ Tag must point to commit with matching pyproject.toml version
- ✅ Mismatch → clear error message
- ✅ No workflow-managed versioning (developer-owned)

---

## IDENTIFIED IMPROVEMENTS

### Current Issues
1. **Docker build duplication**: docker.yml and release.yml both build Docker images
2. **Security scanning only in release**: pip-audit + bandit missing from main CI
3. **Reports not published**: Test reports, coverage, bandit/trivy results live on artifacts, never reach GitHub Pages
4. **Release docker job incomplete**: Extract metadata present, push missing
5. **Caching inefficient**: Multiple jobs re-install dependencies
6. **Version sync unvalidated**: No check that tag matches pyproject.toml

### Scope of Changes
- **Workflow consolidation**: Merge docker.yml logic into ci.yml; use reusable workflows
- **Security scanning**: Move pip-audit + bandit to main CI; add Trivy scan results to pages
- **Dependency autofix**: Implement pip-audit autofix with test validation
- **Report publishing**: Auto-upload coverage, test reports, scan results to GitHub Pages
- **Version validation**: Add sync check in release.yml before docker build
- **Pages enhancement**: Deploy docs + reports from both main and release tags

---

## NEXT HANDOFFS

1. **Security-Engineer** → Vulnerability scanning policy + publication strategy (IN PROGRESS)
2. **Platform-Infrastructure** → Workflow consolidation, pip-audit autofix, version validation, pages enhancement
3. **Tester** → Validate autofix logic and release workflow
4. **Documentation-Writer** → Update release docs and GitHub Pages strategy

