# Agentic Coding Operating Profile

Status: retained v1 execution-profile reference; non-authoritative for current work.

This document is retained for deliberate inspection of the v1 repository state
and its cross-referenced operational history. It is not mandatory routing,
workflow, product, architecture, test, validation, or publication doctrine.
For current work, follow AGENTS.md, PRODUCT.md, and CURRENT.md.

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
work; use convergence-based focused cycles, coherent checkpoint commits, and
separate affected-lane and broad-validation jobs. Internal milestones need not
become separate PRs.

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

## Convergence and checkpoint posture

ROUTINE and other small repairs use the lightest safe workflow: one narrow
surface, one focused test, one correction cycle when sufficient, one validation
pass, and one commit. Do not force INTENSIVE ceremony onto tiny work.

Substantial phases use the standard convergence-and-checkpoint workflow posture
with the selected canonical agent execution profile. The INTENSIVE agent
execution profile additionally expects multiple coherent milestones and
separately staged affected-lane and broad-validation jobs for one large
integration outcome.

For substantial implementation, evaluate every focused red cycle using the
failure count, failed node IDs, causal classification, whether the set is
shrinking, flat, or expanding, and the next bounded correction. A red focused
test is diagnostic information, not an automatic stop.

Continue when failures decrease materially, share one causal explanation, and
directly imply a correction inside the licensed architectural surface without a
new product or authority decision. Stop when failures are flat or expanding for
two consecutive focused cycles, cross into an unrelated responsibility, require
a new product/authority/compatibility decision, require live calls, secrets,
private data, or destructive Git, or genuinely exhaust the authorized budget.
Do not use a fixed maximum red-cycle count as the ordinary default. A phase may
set a stricter retry limit only for a material live-call or external-cost budget,
irreversible operation, explicitly bounded proof, or flaky-infrastructure leash.

A causal cluster is the bounded producer, schema, reducer, consumer, and focused
test path affected by one implementation change. Direct integration fallout may
remain in that cluster: a schema exposing a missing compatibility alias, a
validator moving a negative fixture's failure earlier, a directly implied
consumer or adapter correction, or an omitted transition in the same authority
path. Report meaningful expansion; a newly touched file is not automatically an
unrelated surface. Preserve a stronger validator and update the fixture,
expected failure point, or narrow compatibility adapter instead of weakening
validation solely to restore historical execution order. Stop when the work
enters another product responsibility or needs a genuine architecture decision.

License substantial integration by bounded architectural responsibility: name
the producer, authority transition or reducer, downstream consumer, focused
acceptance path, and preserved product behavior. This permits only directly
necessary files and never unrelated product systems, parallel authority,
provider/retrieval behavior, prompt/model routing, live execution, compatibility
renames, or broad cleanup. Use rigid file allowlists only for genuinely tiny,
fully known repairs.

Create a coherent local checkpoint when a producer/consumer seam or schema/
reducer transition becomes coherent, a product-path milestone passes focused
acceptance, work moves into affected-lane or broad validation, or work must stop.
A checkpoint has a consistent ownership model, green directly owning tests or
one exact blocker, a reviewed continuation diff, and no secrets, private output,
generated artifacts, or unrelated files. Before affected-lane, full-suite, or
baseline-parity validation, require a reviewable local commit. When blocked,
leave the last coherent checkpoint clean or only the exact reported unresolved
edit. A checkpoint is not phase completion, publication permission, merge
approval, full-suite success, baseline parity, or product correctness; never use
one to hide incoherence or bypass exact-diff and architecture review.
