# ScryRaven Build / Proof / Repair Playbook

Status: Recommended repo-tracked playbook for product-engineering phases.
Suggested repo path: `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`

Historical note: this file used to be titled Architecture Groove / Prove Codex
Playbook. That phrase is retired as active workflow language. Build / Proof /
Repair is the active phase operating system.

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

## Phase operating system

Build / Proof / Repair is the active phase operating system. Every phase must
name exactly one delivery mode:

```text
Mode: BUILD | PROOF | REPAIR
```

"Prove Mode" is retired as a global workflow label. Proof is only a phase mode
under Build / Proof / Repair, and it is an exception with a leash, non-claims, a
named blocker, and a mandatory next Build/product checkpoint.

- **BUILD** is the default. It must move a user-style question closer to usable
  answer output through ordinary product/CLI/app execution or a reviewable
  product-path dry-run artifact.
- **PROOF** is a leashed exception. It answers one named uncertainty that blocks
  Build work and must name the next Build/product checkpoint.
- **REPAIR** fixes a named defect in a product-moving path or in the
  repo-visible operating system that governs product-moving work.

Skeptical outside-reviewer question:

```text
Is this finally building the app, or is it building convincing apparatus around the app?
```

A phase brief is invalid if a skeptical reviewer could fairly describe the
deliverable as "a nice collection of harnesses" and the ordinary product path
still cannot demonstrate the claimed behavior.

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

Use a tiny slice when the brief licenses one narrow seam, one high-custody
surface, or one uncertain migration step. The plan may be only two or three
bullets.

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

### Local/live validation phase

Use a live validation phase only when live validation is explicitly scoped with a
query class, run cap, provider/model/search/fetch/read budget, packet path,
redaction plan, decision, and stop condition. Otherwise live ScryRaven/proplex
provider, model, search, or retrieval calls remain disabled.

## Product path requirement for Build and product-facing Repair

Every Build or product-facing Repair phase must state:

```text
Ordinary entrypoint:
User-style demonstration input:
Forbidden substitute outputs:
Product-path pass condition:
Product-path fail condition:
```

Forbidden substitute outputs for product-path claims:

- harness-only path
- fixture-only path
- proof-only script
- replay-only path
- packet-only artifact
- projection-only artifact
- docs-only doctrine
- shadow vertical slice

Pass condition: a user-style input enters through the ordinary product/CLI/app
path and produces the claimed reviewable output.

Fail condition: the ordinary product path cannot consume the change. Stop with a
blocker report instead of demonstrating the behavior beside the product.

## Capability inventory / reuse-first gate

Before implementing new code, any phase touching mature authority or product
surfaces must inventory the existing repo-visible capability and classify each
relevant surface as `REUSE`, `ADAPT`, `UPGRADE`, `RETIRE`, or `REPLACE`.
If existing current capability may already own the responsibility, stop for
capability inventory instead of building a parallel surface.

Trigger surfaces include:

- D-prime / DPrime
- Analyst / EvidenceRelativeAnalysisPacket
- source authority
- source obligation
- citation eligibility / citation-source handoff
- SufficiencyReadiness
- FinalAnswerPacket / FAP
- Author
- SemanticObservation
- ComponentCoverage
- RunKernel admission / RunKernel authority
- follow-up / recovery
- SearchPlanner / query planner
- model-assisted planning
- FastModel / SmartModel
- Scrutineer
- multi-source
- multi-component
- EvidenceLedger
- fetch/read
- provider acquisition
- evidence triage
- source gateway / answer gateway / readiness

Required inventory table:

```text
Surface:
Existing owner module/doc:
Current consumer:
Current status:
Action: REUSE | ADAPT | UPGRADE | RETIRE | REPLACE
Why not duplicate:
Tests/guards:
```

Reuse-first means the phase should prefer adapting existing product-consumed or
current internal authority surfaces over introducing new authority seams. A
`REPLACE` classification must explain why `REUSE`, `ADAPT`, and `UPGRADE` are
insufficient and how the old path will be deleted, demoted, bypassed,
subordinated, or scheduled for retirement.

D-prime downstream machinery already includes source-obligation authority,
citation-source handoff, a single-lane answer path, follow-up re-entry, and
same-lane multi-source scrutiny in the status path. Generic dogfood or adapter
work near source-obligation, citation readiness, FAP, Author, or answer-path
readiness should inventory those D-prime surfaces first and prefer
reuse/adaptation over rebuilding source-obligation or citation-readiness
machinery.

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

Proceed autonomously for relevant file inspection, scoped implementation,
in-scope test additions or updates, in-scope test failure fixes, stale docs links
or formatting caused by the phase, formatting, lint, pre-commit fixes,
final-bundle preparation, and PR creation when explicitly authorized by the
phase brief.

Stop and ask for a user decision only for product choices, architecture forks not
resolved by the brief or repo doctrine, unlicensed or closed-this-phase surface
changes, live validation or live-call budget, secrets/private data, destructive
git, merge/squash/rebase/force-push, broad scope expansion, or unresolved failing
tests whose fix changes the meaning of the phase.

Use this stop packet when escalation is required:

```text
STOP REASON:
scope_break | surface_boundary_uncertainty | live_budget_request |
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

If the phase prompt approves Build / Proof / Repair Path B work, Codex may:

- inspect repo files;
- edit within scope;
- run offline tests;
- add in-scope tests/harnesses only when the phase labels them and names the
  runtime consumer, deadline, and exit condition;
- add compact validation artifacts tied to the phase;
- make local checkpoint commits;
- fix in-scope failures;
- self-review;
- push the completed branch and create a PR only if the phase brief explicitly
  allows phase-end publication.

## Not allowed by default

Codex must not merge, squash merge, rebase, force-push, delete branches, reset,
clean destructively, alter `main`, run live ScryRaven/proplex provider/model/search
calls, access secrets/env/API keys, inspect DBs/private logs/generated
outputs/caches/virtualenvs unless explicitly scoped, or change closed-this-phase
surfaces outside phase scope.

## Surface vocabulary

Use current phase-boundary words precisely:

- **Licensed surface:** explicitly opened by the phase brief.
- **Target surface:** the thing this phase is meant to inspect, change, reduce,
  move, simplify, retire, or strangle.
- **High-custody surface:** important/risky behavior that may be changed only
  with narrow scope, named tests, and stop conditions.
- **Closed-this-phase surface:** do not touch in this phase.
- **Historical surface:** retained as record, not current doctrine or product
  path.
- **Strangler target:** a surface to reduce, bypass, demote, subordinate, or
  delete over time.

"Protected" is retired as active phase-control vocabulary because it can imply
"do not touch." When a surface is important and risky but intended to be changed,
call it a high-custody target or strangler target, not protected.

Treat unexpected changes to high-custody or closed-this-phase surfaces as stop
conditions. Common examples include Analyst/Economist/Author handoff, Analyst
skip behavior, Economist shortcut behavior, raw quantitative/Economist material
exposure, Scrutineer policy, provider routing, prompt semantics, source
ranking/filtering, persistence schema, weak-corpus/source-class/retrieval-stop
runtime behavior, and live-run behavior.

`core/pipeline_orchestrator.py` is not architecture-successful merely because a
phase leaves it untouched. It is a coordination shell with remaining authority
debt. It may be closed-this-phase in ordinary product behavior phases, and it may
be a licensed target surface or strangler target in orchestrator-strangulation
phases.

## Current authority and product-consumption vocabulary

Use these labels instead of allowing "current authority path" to imply that the
installed app/product consumes the surface:

- **current internal authority path:** canonically owned or reduced by
  RunKernel/RunAuthority or another named current authority, but not necessarily
  product-visible.
- **current product-consumed path:** consumed by ordinary CLI/app/product flow.
- **fixture-only proof:** fixture-backed proof of a seam, not product-consumed.
- **offline harness / proof-only harness:** offline scaffold or script, not live
  and not product-consumed unless the ordinary path consumes it.
- **integration-staging harness:** temporary scaffold while wiring a named
  product consumer.
- **product-facing dry-run output:** reviewable output through a local/dry-run
  path; useful but not live product correctness.
- **live product path:** explicitly licensed live product execution that reaches
  the claimed product output.
- **historical/proof-only debt:** retained proof or harness history that must not
  be cited as current product progress.

A surface may be current internal authority and still have only fixture-only,
offline-harness, or product-facing-dry-run proof. Use current product-consumed
path only when ordinary product/CLI/app flow actually consumes the behavior.

## Harness labels and expiration

Every new harness, proof-only script, replay path, packet-only demo, or
non-product scaffold must carry exactly one label:

- **PRODUCT-PATH-REGRESSION:** a harness/test guarding behavior already consumed
  by the ordinary product path. Healthy and durable.
- **SEAM-DIAGNOSTIC:** a temporary harness to isolate a failure or uncertainty at
  one seam. Must name the product seam and exit condition.
- **INTEGRATION-STAGING:** a temporary scaffold used while wiring a real product
  path. Must name the ordinary runtime consumer and integration deadline.
- **EXPLORATORY-PROOF-ONLY:** non-product learning/proof. Must not be named like
  product behavior and must have an integrate/reject/delete decision.
- **SHADOW-PRODUCT-HARNESS:** a product-shaped alternate path beside the product.
  This is failure unless explicitly authorized for review-only diagnosis.

Required fields:

```text
Harness label:
Ordinary product path guarded or fed:
Runtime consumer:
Why ordinary product-path work cannot be done directly:
Integration deadline:
Exit condition:
Why this is not a shadow product path:
Forbidden interpretation:
```

A harness created in phase N should be consumed, converted to a product-path
regression guard, deleted, or marked historical/proof-only debt by phase N+1. It
may survive to N+2 only if N+1 exposed a specific blocker and N+2 is explicitly
the integration/retirement phase. After N+2, unconsumed harness/proof scaffolding
is historical/proof-only debt by default and must not be cited as product
progress.

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

The packet should include exact queries, full final answers, final cited URLs,
visible source sections/snippets, sanitized CLI-visible telemetry, and
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
11. Licensed/closed-this-phase/target/high-custody surface changes, if any
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
