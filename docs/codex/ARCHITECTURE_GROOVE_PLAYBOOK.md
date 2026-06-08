# ScryRaven Architecture Groove / Prove Codex Playbook

Status: Recommended repo-tracked playbook
Suggested repo path: `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`

## Purpose

This playbook contains repeated workflow rules for ScryRaven Codex phases. Future
phase prompts should be short and should reference this playbook, the
[Codex Guidance Map](CODEX_GUIDANCE_MAP.md), and any phase-specific guide rather
than re-stating the whole operating manual.

ScryRaven is the public project name for this repository. Historical docs may
still mention earlier working names such as ProPlex, FauxPlex, and FauxPlexity;
the `proplex` package, `python -m proplex`, `PROPLEX_*` environment names,
`proplex.db`, and `proplex_*` state keys remain supported compatibility surfaces
unless a phase explicitly removes them.

## Path B branch / PR workflow

Default workflow:

```text
1. Start from updated main.
2. Create/use a phase branch.
3. Inspect the relevant repo-visible files.
4. Choose the right phase size and write a short plan.
5. Implement within scope.
6. Add/update in-scope tests and docs links caused by the phase.
7. Run required offline tests/checks.
8. Fix in-scope failures.
9. Self-review the diff.
10. If the phase brief allows publication, push the completed branch and create a PR.
11. Return one final phase bundle.
```

GitHub is the review surface for a completed phase branch, not a sub-step
synchronization layer. Codex must not merge the PR.

## Standard setup

```powershell
git switch main
git pull --ff-only origin main
git status -sb
git switch -c <phase-branch>
```

When giving PowerShell to the user for paste-back diagnostics, include a final
`Set-Clipboard` summary block. Prefer robust `git -C <repo>` commands over
brittle inline `cd ...; git ...` expressions.

## Phase-size choice

Do not force every phase into a tiny slice. Pick the smallest phase shape that
can satisfy the brief without creating avoidable user coordination work.

### Tiny slice phase

Use a tiny slice when the brief licenses one narrow seam, one protected surface,
or one uncertain migration step. The plan may be only two or three bullets.

### Bundled multi-step phase

Use a bundled phase when the brief already names a coherent set of related edits,
tests, doc links, and cleanup. Create a compact execution plan instead of asking
the user to approve each small implementation detail. Use
[EXECUTION_PLAN_TEMPLATE.md](EXECUTION_PLAN_TEMPLATE.md) when the bundle has
multiple checkpoints, runtime consumers, or old authority paths.

### Docs/design phase

Use a docs/design phase when the requested output is guidance, architecture
inventory, phase planning, or review material. Keep runtime/app code closed.
Docs-only phases may still fix in-scope links, formatting, and stale guidance
created or exposed by the doc edits.

### Review-only phase

Use a review-only phase when the user asks for an audit, inventory, or critique
without implementation. Do not modify code unless the brief explicitly expands
from review into implementation.

### Local/live dogfood phase

Use a dogfood phase only when live validation is explicitly scoped with a query
class, run cap, provider/model/search budget, packet path, redaction plan,
decision, and stop condition. Otherwise live ScryRaven/proplex provider, model,
search, or retrieval calls remain disabled.

## Codex Cloud and local validation roles

### Codex Cloud implementation role

Codex Cloud should inspect repo-visible files, plan briefly, execute scoped work,
add or update in-scope tests/docs, run focused offline checks, fix in-scope
failures, self-review, and open a PR when explicitly authorized.

### Local desktop validation / dogfood role

Local desktop validation is for user-run app review, secrets-backed live calls,
private artifacts, DB inspection, caches, local packets, and output-quality
judgment. Codex Cloud must not assume those artifacts are repo files and must not
request them unless the phase explicitly scopes safe redacted access.

## Bounded autonomy and decision points

Codex should reduce user coordination burden. Do not stop for issues that are
fixable within the phase scope.

Proceed autonomously for:

- relevant file inspection;
- scoped implementation;
- in-scope test additions or updates;
- in-scope test failure fixes;
- stale docs links or formatting caused by the phase;
- formatting, lint, and pre-commit fixes;
- final-bundle preparation;
- PR creation when explicitly authorized by the phase brief.

Stop and ask for a user decision only for:

- product choices;
- architecture forks not resolved by the brief or repo doctrine;
- unlicensed protected-surface changes;
- live validation or live-call budget;
- secrets, private data, `.env`, DB rows, private logs, caches, raw provider
  payloads, raw prompts, full raw traces, or local output packets;
- destructive git (`reset`, destructive `clean`, branch deletion, history rewrite);
- merge, squash merge, rebase, or force-push;
- broad scope expansion;
- unresolved failing tests whose fix changes the meaning of the phase.

Use this stop packet when escalation is required:

```text
STOP REASON:
scope_break | protected_surface_uncertainty | live_budget_request |
secret_or_generated_data_access_needed | destructive_git_needed |
merge_or_destructive_git_needed | design_decision | tests_reveal_architecture_choice

WHAT HAPPENED:
...

OPTIONS:
A. ...
B. ...
C. ...

RECOMMENDATION:
...
```

## Allowed by default in a phase

If the phase prompt approves Architecture Groove / Prove Mode, Codex may:

- inspect repo files;
- edit within scope;
- run offline tests;
- add in-scope tests/harnesses;
- add compact validation artifacts tied to the phase;
- make local checkpoint commits;
- fix in-scope failures;
- self-review;
- push the completed branch and create a PR only if the phase brief explicitly
  allows phase-end publication.

## Not allowed by default

Codex must not:

- merge;
- squash merge;
- rebase;
- force-push;
- delete branches;
- reset;
- clean destructively;
- alter `main`;
- run live ScryRaven/proplex provider/model/search calls;
- access secrets/env/API keys;
- inspect DBs/private logs/generated outputs/caches/virtualenvs unless explicitly
  scoped;
- change protected surfaces outside phase scope.

## Protected surfaces

Protected surfaces are high-custody and licensable, not categorically forbidden.
A phase may change one only when the brief explicitly names the surface, allowed
behavior, tests, and validation boundary. Treat unexpected changes as stop
conditions:

- Analyst/Economist/Author handoff;
- Analyst skip behavior;
- Economist shortcut behavior;
- raw quantitative/Economist material exposure;
- Scrutineer policy;
- provider routing;
- prompt semantics;
- source ranking/filtering;
- persistence schema;
- weak-corpus/source-class/retrieval-stop runtime behavior;
- live-run behavior.

## AG-89+ RunAuthority work

For AG-89+ authority-collapse phases, use
[RUNAUTHORITY_IMPLEMENTATION_GUIDE.md](RUNAUTHORITY_IMPLEMENTATION_GUIDE.md).
The legacy Controller handoff playbook is not the default doctrine for those
phases. Authority-collapse success requires runtime consumption by the intended
consumer and deletion, demotion, bypass, subordination, or scheduled retirement
of the old authority path.

Trace-only, storage-only, wrapper-only, prompt-visible-only, or test-only
authority is failure unless the phase is explicitly passive, docs-only, or
instrumentation-only.

## Live validation artifacts

Live validation uses money and should produce reusable review material. Unless
explicitly waived, every live validation/smoke phase should produce:

1. A committed validation note under `docs/validation/` when durable phase
   history is useful.
2. A local, ignored output-quality review packet under
   `output/ag##_output_quality_review_packet.md`.

The local packet must not be committed. Legacy naming note: the terms `truth
review`, `truth packet`, and `live truth review` are retired. Use
`output-quality review packet` for local answer/source-quality review artifacts.

It should include exact queries, full final answers, final cited URLs, visible
source sections/snippets, sanitized CLI-visible telemetry, and
unavailable-telemetry notes.

It must not include `.env`, API keys/secrets, DB rows, raw provider payloads, raw
prompts, full traces, private logs, caches, or unrelated generated outputs.

Validation phases should confirm:

```powershell
git check-ignore -v output/ag##_output_quality_review_packet.md
git ls-files output
```

## Final bundle

Return:

```text
1. Mode and scope
2. Architectural goal and whether met
3. Branch, base commit, HEAD, status
4. Commit list
5. Diff stat
6. Changed files/functions/classes
7. Tests added/changed
8. Commands run and results
9. Behavior changes
10. Answer-contract / fulfillment / handoff changes, if any
11. Protected-surface changes, if any
12. Telemetry/validation artifacts added, with consumer/decision/deletion criteria
13. Risky-surface scan
14. Live validation used or not used
15. Local output-quality review packet created? yes/no/not applicable
16. Branch pushed? yes/no
17. PR created? yes/no, URL if available
18. Known rough edges
19. Recommended final action
```

## Phase-end PR creation

If the phase brief says phase-end publication is allowed:

```text
After tests and self-review, Codex may push the completed branch and create a PR into main.
Codex must not merge.
```
