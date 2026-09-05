# Compact Phase Brief Template

Status: retained v1 phase-brief reference; non-authoritative for current work.

This document is retained for deliberate inspection of the v1 repository state
and its cross-referenced operational history. It is not mandatory routing,
workflow, product, architecture, test, validation, or publication doctrine.
For current work, follow AGENTS.md, PRODUCT.md, and CURRENT.md.

Read `CODEX_GUIDANCE_MAP.md`, `ARCHITECTURE_GROOVE_PLAYBOOK.md`, and the routed
owner documents relevant to the work. Add only applicable sections from
`PHASE_BRIEF_ADDENDA.md`.

```text
Phase:
Mode: BUILD | PROOF | REPAIR
Usable-answer verdict target: YES | NO-BUT-JUSTIFIED

Agent execution profile recommendation: ROUTINE | DEEP | INTENSIVE | DELEGATED
Reason:
Human-selection reminder: the operator selects the actual model and reasoning/intelligence level; this recommendation does not alter authority.

Outcome:
<One coherent product or repair result.>

Constraints:
- In-scope surfaces:
- Closed-this-phase surfaces:
- Existing machinery to reuse:
- Old-path treatment:

Current factual baseline:
- Base/required prior merge:
- Facts verified from the repository:
- Product-moving failure prevented, for repo-doc/process Repair:
- Mandatory next Build/product checkpoint, when applicable:

Ordinary path, for BUILD or product-facing REPAIR:
- Ordinary entrypoint:
- User-style input:
- Runtime consumer:
- Reviewable output delta:
- Pass condition:
- Forbidden substitutes: harness-only, fixture-only, proof-only, replay-only, packet-only, projection-only, docs-only, or shadow paths.

Completion criteria:
- The full scoped outcome reaches its named consumer.
- Old or duplicate ownership is deleted, demoted, bypassed, subordinated, or scheduled for retirement.
- Required docs and practical regression guards are current.

Verification:
- Focused checks during implementation:
- Required broader offline regression checks:
- Full branch-diff review against main:
- Final skeptical-maintainer review:
- Explicitly not run:

Stop conditions:
- Named product decision or unresolved architecture fork.
- Unlicensed or closed-surface change.
- Live-call or private-data access not explicitly licensed.
- Destructive Git, merge, rebase, force-push, or main mutation.
- Failure whose repair would change scope or product meaning.

Publication authorization:
- none | checkpoint commits | commit | push branch | open draft PR
- Do not merge.

Final report:
- Outcome and scope
- Material changes
- Verification evidence
- Self-review findings and fixes
- Risks and nonproofs
- Git/PR status
- Recommended next action
```

Small coherent phases may be brief. Larger coherent vertical slices are allowed
when they share one ordinary consumer and rollback boundary; use
`EXECUTION_PLAN_TEMPLATE.md` for internal milestones and the conditional
large-phase execution posture in `PHASE_BRIEF_ADDENDA.md` rather than restating
the operating manual here.
