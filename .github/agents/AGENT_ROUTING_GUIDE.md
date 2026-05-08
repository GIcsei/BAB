# AGENT ROUTING GUIDE - BAB

## Default First Delegate

- Ambiguous scope, unclear acceptance criteria, or mixed goals -> product-owner
- Architecture, sequencing, or layer boundary concern -> tech-lead
- Well-scoped implementation -> owning specialist below

## Ownership Map

- FastAPI routes, schemas, endpoint docs, OpenAPI drift -> api-surface
- Service logic, orchestration, bug fixes, behavior-preserving refactors -> backend-implementer
- Firebase, Firestore, scheduler, runtime integration, Docker/TrueNAS-sensitive work -> platform-infrastructure
- Auth, token lifecycle, credential storage, secret handling, deserialization risk, security review -> security-engineer
- Pytest coverage, repros, regressions -> tester
- Readiness review and acceptance audit -> qa-engineer
- README, docs, TODO and memory hygiene -> documentation-writer

## Preferred Execution Sequences

### Bug fix or small refactor
1. product-owner (only if unclear)
2. tech-lead (only if cross-layer)
3. backend-implementer or owning specialist
4. tester
5. qa-engineer (if risk remains)
6. documentation-writer (if docs changed)

### API contract or schema change
1. product-owner (if semantics changed)
2. tech-lead (if multiple layers move)
3. api-surface
4. backend-implementer or platform-infrastructure as needed
5. tester
6. documentation-writer

### Runtime, scheduler, Firebase, or TrueNAS-sensitive work
1. tech-lead (if scope spans multiple files or layers)
2. platform-infrastructure
3. security-engineer (if secrets/auth/data risk involved)
4. tester
5. qa-engineer
6. documentation-writer

## Mandatory Reviews

- Auth, credential, token, or unsafe deserialization change -> security-engineer
- New or changed endpoint, schema, or API docs -> api-surface
- Scheduler, job restore, Firestore, or deployment/runtime integration -> platform-infrastructure
- Any code change with risk or uncertain test coverage -> tester
- Release-style review or user-requested review -> qa-engineer
