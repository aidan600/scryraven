# Architecture Groove / Prove Codex Playbook

Status: Recommended repo-tracked playbook
Suggested repo path: `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`

## Purpose

This playbook contains repeated workflow rules for ProPlex/FauxPlex Codex architecture phases.

Future phase prompts should be short and should reference this playbook instead of re-stating the whole operating manual.

## Path B

Default workflow:

```text
1. Start from updated main.
2. Create/use a phase branch.
3. Implement within scope.
4. Make local checkpoint commits if useful.
5. Run required offline tests/checks.
6. Fix in-scope failures.
7. Self-review.
8. If the phase brief allows publication, push the completed branch and create a PR.
9. Return one final phase bundle.
```

GitHub is the review surface for a completed phase branch, not a sub-step synchronization layer.

## Standard setup

```powershell
git switch main
git pull --ff-only origin main
git status -sb
git switch -c <phase-branch>
```

When giving PowerShell to the user for paste-back diagnostics, include a final `Set-Clipboard` summary block. Prefer robust `git -C <repo>` commands over brittle inline `cd ...; git ...` expressions.

## Allowed by default in a phase

If the phase prompt approves Architecture Groove / Prove Mode, Codex may:

- inspect repo files,
- edit within scope,
- run offline tests,
- add in-scope tests/harnesses,
- add compact validation artifacts tied to the phase,
- make local checkpoint commits,
- fix in-scope failures,
- self-review,
- push the completed branch and create a PR only if the phase brief explicitly allows phase-end publication.

## Not allowed by default

Codex must not:

- merge,
- squash merge,
- rebase,
- force-push,
- delete branches,
- reset,
- clean destructively,
- alter `main`,
- run live ProPlex/provider/model/search calls,
- access secrets/env/API keys,
- inspect DBs/private logs/generated outputs/caches/virtualenvs unless explicitly scoped,
- change protected surfaces outside phase scope.

## Protected surfaces

Treat unexpected changes as stop conditions:

- Analyst/Economist/Author handoff,
- Analyst skip behavior,
- Economist shortcut behavior,
- raw quantitative/Economist material exposure,
- Scrutineer policy,
- provider routing,
- prompt semantics,
- source ranking/filtering,
- persistence schema,
- weak-corpus/source-class/retrieval-stop runtime behavior,
- live-run behavior.

## Live validation artifacts

Live validation uses money and should produce reusable review material.

Unless explicitly waived, every live validation/smoke phase should produce:

1. A committed validation note under `docs/validation/` when durable phase history is useful.
2. A local, ignored output-quality review packet under `output/ag##_output_quality_review_packet.md`.

The local packet must not be committed.

Legacy naming note: the terms `truth review`, `truth packet`, and `live truth review` are retired. Use `output-quality review packet` for local answer/source-quality review artifacts.

It should include exact queries, full final answers, final cited URLs, visible source sections/snippets, sanitized CLI-visible telemetry, and unavailable-telemetry notes.

It must not include `.env`, API keys/secrets, DB rows, raw provider payloads, raw prompts, full traces, private logs, caches, or unrelated generated outputs.

Validation phases should confirm:

```powershell
git check-ignore -v output/ag##_output_quality_review_packet.md
git ls-files output
```

## Stop packet

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
