# Phase Brief Addenda

Status: Conditional fields for the compact phase brief.

Use only the addenda triggered by the phase. Do not copy empty sections into a
brief. Standing procedure remains in the root contract and playbook.

## Local Cursor Windows workspace

Use only when a phase uses a disposable local Cursor Windows worktree. Follow
the [Cursor Local Windows Phase Execution Rule](CURSOR_LOCAL_WINDOWS_PHASE_EXECUTION_RULE.md)
rather than duplicating its procedure.

```text
Local workspace:
- Phase root:
- Worktree:
- Cache:
- Tmp:
- Evidence:
- Final:
- Cursor root is readable and not ignored: YES
```

## Large-phase execution posture

Use only for substantial integration work; tiny repairs retain the lightweight
workflow in the operating profile.

```text
Agent execution profile: ROUTINE | DEEP | INTENSIVE | DELEGATED
Large-phase workflow posture:
Apply convergence evaluation, causal-cluster scope, coherent milestone
checkpoints, and separated validation jobs.

Licensed architectural surface:
- Named producer:
- Authority transition or reducer:
- Downstream consumer:
- Focused acceptance path:
- Product behavior preserved:

Convergence rule:
Continue while failures decrease and remain within one causal cluster.
Stop on divergence, unrelated responsibility, or architectural uncertainty.

Checkpoint policy:
Create coherent local checkpoint commits at milestones and before expensive validation.

Validation separation:
Focused implementation -> candidate checkpoint and exact-diff review -> affected
lanes -> publication -> full-suite or parity validation -> independent final review.

Acceptance owner:
One Strategy/Review chat owns the active acceptance target.
```

## Proof-only leash

```text
Proof class:
Named Build blocker or technical question:
Why product-path work is not licensed or safe now:
Scope/time cap:
Current-path consumer or decision unlocked:
Existing machinery reused:
Proof-only machinery introduced:
Integrate, reject, or delete decision:
Mandatory next Build/product checkpoint:
Explicit nonproofs:
```

No second Proof phase for the same blocker is allowed without explicit user
approval. Follow `PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md`.

## Live-validation license

Use only when a phase licenses live ScryRaven/proplex provider, model, search,
fetch/read, retrieval, or ordinary-product execution. Follow the playbook
local/live-validation rules. Maximum PRODUCT runs define experimental
authority. Do not add a provider/model/search/fetch/read budget as a default
license field.

Hard model/search/read/embedding attempt ceilings, token ceilings, and dollar
ceilings belong under additional numeric safety fields only when explicitly
requested by the maintainer, the experiment tests a budget/resource
constraint, material exposure risk warrants them, or the installed
authorization mechanism mechanically requires numeric fields. When those
fields are mechanically required, they are non-interfering safety-compilation
fields covering the lawful product execution relevant to the observation, not
an arbitrary micro-budget. When `max_run_usd` is mechanically required for
current maintainer-directed local development and no other value is specified,
use the standing $10 USD emergency per-run fuse; it is not expected spend or
product policy.

For a repeated tiny observation using an already-settled authorization
posture, instruct the agent to bind/reuse that posture and execute, not to
research or derive a new budget.

```text
Exact PRODUCT/validation target:
Maximum PRODUCT runs:
Retry/replacement authority, if relevant:
Expected cost/risk posture:
Operator path:
Command/harness:
Sanitized output path:
Decision:
Stop condition:
Additional numeric safety fields, only when required:
```

Absent this completed addendum, live validation remains disabled.

## New harness or non-product scaffold

```text
Harness label: PRODUCT-PATH-REGRESSION | SEAM-DIAGNOSTIC | INTEGRATION-STAGING | EXPLORATORY-PROOF-ONLY | SHADOW-PRODUCT-HARNESS
Observed failure or approved hard prerequisite:
Exact unresolved distinction:
Existing owners already tried:
Demonstrated observability or reproducibility gap:
Production-owned boundary injected or observed:
Named immediate consumer:
Why the dependency cannot reasonably be completed in the consumer phase:
Decision the harness will make:
Duplicate-observation check:
Maximum infrastructure PRs before consumption:
Durable ownership, integration, replacement, or removal condition:
Mandatory next supported-product checkpoint:
Forbidden interpretation:
```

A future consumer is valid only as the approved immediate successor, with a real
dependency, no equivalent seam, no intervening infrastructure phase, and an
explicit evidence target and exit condition. Installation completes nothing
until the named consumer uses it, evidence is produced, and a product or
architecture decision changes. Follow the proof-class gate and playbook.

## High-custody migration inventory

```text
Surface:
Existing owner module/doc:
Current consumer:
Current status:
Action: REUSE | ADAPT | UPGRADE | RETIRE | REPLACE
Why not duplicate:
Tests/guards:
Old-path treatment:
Rollback boundary:
```

Use one entry per relevant authority or mature capability surface.

## Delegated execution

```text
Main architectural integrator and default writer:
Independent read-heavy workstreams:
Nonoverlapping write ownership, if explicitly needed:
Integration and complete-diff review owner:
```

Start delegation with exploration, tests, triage, summarization, or independent
review. Parallel edits to overlapping files are forbidden. Independent writers
require explicit nonoverlapping worktree ownership. See
`AGENTIC_CODING_OPERATING_PROFILE.md`.
