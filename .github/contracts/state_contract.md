# STATE CONTRACT

## Purpose

Defines live machine state governance for memory/session-state.json.

## Ownership

Only scrum-master updates:
- activeRequest
- currentStage
- currentOwner
- nextHandoff
- agentQueue

Specialists may propose updates to:
- blockers
- notes
- lastUpdated

## Required Shape

session-state.json must include:
- activeRequest
- currentStage
- currentOwner
- nextHandoff
- agentQueue
- blockers
- locks
- lastUpdated
- notes

## Locking

Before writing live state:
1. Check locks.memory
2. Acquire if free
3. Write minimal valid update
4. Release immediately

## Consistency

currentStage/currentOwner/nextHandoff must match active-context.md.
