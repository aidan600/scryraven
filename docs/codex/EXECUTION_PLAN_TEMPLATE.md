# Codex Multi-Step Execution Plan Template

Status: retained v1 execution-plan reference; non-authoritative for current work.

This document is retained for deliberate inspection of the v1 repository state
and its cross-referenced operational history. It is not mandatory routing,
workflow, product, architecture, test, validation, or publication doctrine.
For current work, follow AGENTS.md, PRODUCT.md, and CURRENT.md.

Suggested repo path: `docs/codex/EXECUTION_PLAN_TEMPLATE.md`

Use this template when a phase is larger than a tiny slice but still bounded by
the brief. Keep it short enough to execute without repeatedly asking the user for
small coordination decisions. It expands the compact
`Outcome / Constraints / Verification` contract; it does not create additional
approval gates or automatic PR boundaries.

```text
Phase goal:
- ...

Agent execution profile:
- ROUTINE | DEEP | INTENSIVE | DELEGATED (advisory; human-selected setting)

Phase type:
- tiny slice | bundled multi-step | docs/design | review-only | local/live dogfood

Opened surfaces:
- Files, modules, docs, tests, or licensed surfaces explicitly in scope.

Closed surfaces:
- Runtime/app behavior, live calls, secrets/private artifacts, closed surfaces,
  or historical docs that remain out of scope.

Autonomy level:
- Codex may inspect, edit, test, fix in-scope failures, update caused docs links,
  self-review, and create a PR if authorized.
- Codex must stop for product choices, unresolved architecture forks, unlicensed
  or closed-surface changes, live validation, secrets/private data, destructive
  git, merge/rebase/force-push, broad scope expansion, or tests that reveal a
  design decision.

Planned steps/checkpoints:
1. ...
2. ...
3. ...

Expected files/seams:
- ...

Runtime consumers:
- Consumer:
- New authority or state read:
- Proof expected:

Old authority paths to delete/demote/bypass/subordinate:
- Old path:
- Planned status:
- Retirement trigger if retained:

Tests/checks per step:
- Step 1:
- Step 2:

Continuation validation:
- New reproduction:
- Immediate owner checks:
- Targeted static or changed-doc checks:

Coherent-checkpoint validation:
- Full phase-focus proof:
- Immediate producer/consumer checks:
- Complete-diff review:

Final-candidate validation:
- `fast_pr` (ordinary non-docs PR):
- Directly affected durable lane(s), with changed-authority justification:
- Final docs/static checks:
- Exact-head hosted CI:

Focused review corrections default to continuation validation, not a rerun of
the complete phase validation bundle. Use the
[Review-Loop Validation Ramp](VALIDATION_BUCKETS.md#review-loop-validation-ramp)
to decide when broader proof is warranted.

In-scope repair policy:
- Fix focused test failures, formatting/pre-commit issues, stale links caused by
  edits, and small consistency problems across touched docs/code.

Stop conditions:
- Product decision:
- Architecture fork:
- Safety-sensitive or closed surface not licensed:
- Unlicensed live validation:
- Secret/private artifact needed:
- Destructive git or merge/rebase/force-push needed:
- Broad scope expansion:
- Failing tests imply design change:

Final bundle requirements:
- Outcome and scope; material changes; verification evidence.
- Self-review findings and fixes; risks and nonproofs.
- Git/PR status and recommended next action.
- For authority-collapse: old owner, new owner, runtime consumer, consumption
  proof, old-path retirement status, and remaining duplicate-owner risk.
```
