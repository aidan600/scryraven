# Codex Multi-Step Execution Plan Template

Status: Recommended compact template for bundled phases
Suggested repo path: `docs/codex/EXECUTION_PLAN_TEMPLATE.md`

Use this template when a phase is larger than a tiny slice but still bounded by
the brief. Keep it short enough to execute without repeatedly asking the user for
small coordination decisions.

```text
Phase goal:
- ...

Phase type:
- tiny slice | bundled multi-step | docs/design | review-only | local/live dogfood

Opened surfaces:
- Files, modules, docs, tests, or protected surfaces explicitly in scope.

Closed surfaces:
- Runtime/app behavior, live calls, secrets/private artifacts, protected surfaces,
  or historical docs that remain out of scope.

Autonomy level:
- Codex may inspect, edit, test, fix in-scope failures, update caused docs links,
  self-review, and create a PR if authorized.
- Codex must stop for product choices, unresolved architecture forks, unlicensed
  protected-surface changes, live validation, secrets/private data, destructive
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
- Final focused checks:

In-scope repair policy:
- Fix focused test failures, formatting/pre-commit issues, stale links caused by
  edits, and small consistency problems across touched docs/code.

Stop conditions:
- Product decision:
- Architecture fork:
- Protected surface not licensed:
- Live validation/budget needed:
- Secret/private artifact needed:
- Destructive git or merge/rebase/force-push needed:
- Broad scope expansion:
- Failing tests imply design change:

Final bundle requirements:
- Branch/base/HEAD/status.
- Changed files and diff stat.
- Tests/checks run and results.
- Protected surfaces opened/closed.
- Live validation status.
- PR URL if created.
- For authority-collapse: old owner, new owner, runtime consumer, consumption
  proof, old-path retirement status, and remaining duplicate-owner risk.
```
