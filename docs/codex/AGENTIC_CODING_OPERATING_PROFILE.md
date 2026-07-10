# Agentic Coding Operating Profile

Status: Canonical vendor-neutral execution-profile doctrine.

This document helps a human operator choose an execution profile. Profiles
describe task shape and recommended attention; they do not grant authority.

## Profiles

### ROUTINE

Known path, bounded work, and ordinary checks. Prefer a compact plan and the
smallest relevant validation bucket.

### DEEP

Difficult tracing, cross-file logic, authority boundaries, or sensitive review.
Use focused intermediate checks and a complete skeptical diff review.

### INTENSIVE

One large coherent vertical slice crossing several tightly coupled seams. Keep
the ordinary consumer endpoint and compatible rollback boundary as the unit of
work; internal milestones need not become separate PRs.

### DELEGATED

Difficult work with genuinely independent exploration, testing, triage, or
review workstreams. The main agent is the sole architectural integrator and
default writer. Delegated work should begin with read-heavy exploration,
testing, triage, summarization, or independent review.

Parallel edits to overlapping files are forbidden. Independent writers require
explicit nonoverlapping worktree ownership. The main agent reviews and
integrates all delegated findings and remains accountable for the full diff.

## Human-controlled selection

The human operator selects the actual coding agent, model, and reasoning or
intelligence level. The repository does not force or silently escalate a
setting. Another coding agent should use the nearest reliable equivalent.

Reasoning or intelligence level is independent from sandbox and publication
permissions. It never expands scope, filesystem or network access, publication
authority, live-call authority, private-data access, or destructive-operation
authority.

## Current Codex adapter

This mapping is advisory and may change as selectors evolve:

| Profile | Current recommendation |
| --- | --- |
| ROUTINE | Medium |
| DEEP | High |
| INTENSIVE | Extra High |
| DELEGATED | Ultra |

The operator may select a different level. Do not claim a setting was changed
unless the operator or execution environment confirms it.

## Applying a profile

Record only the recommendation needed by the phase brief:

```text
Agent execution profile: ROUTINE | DEEP | INTENSIVE | DELEGATED
Reason: <one sentence>
```

For substantial work, pair the profile with the repository-wide contract:

```text
Outcome:
Constraints:
Verification:
```

Profiles tune attention and coordination. Phase scope, stop conditions,
validation authority, private-data rules, Git authority, and publication
authorization still come from the task prompt and standing repository contract.
