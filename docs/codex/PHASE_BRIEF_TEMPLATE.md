# Codex Phase Brief Template

Status: Recommended repo-tracked template
Suggested repo path: `docs/codex/PHASE_BRIEF_TEMPLATE.md`

Copy this for future phases and fill in only phase-specific details. Keep
prompts compact. Standing workflow, boundary, safety, and publication rules
belong in repo docs such as `AGENTS.md`, `CODEX_GUIDANCE_MAP.md`, and
`ARCHITECTURE_GROOVE_PLAYBOOK.md`; phase prompts should not restate the whole
operating manual.

```text
<PHASE NAME>
Build / Proof / Repair Path B approved.

Historical wording note:
- Do not call this Architecture Groove / Prove Mode.
- “Prove Mode” is retired as a global workflow label.
- Proof is only a phase mode under Build / Proof / Repair, and it is an exception
  with a leash, non-claims, a named blocker, and a mandatory next Build/product
  checkpoint.

Read:
docs/codex/CODEX_GUIDANCE_MAP.md
docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md

Also read when relevant:
- docs/codex/EXECUTION_PLAN_TEMPLATE.md for bundled multi-step phases
- docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md for AG-89+ authority-collapse phases
- docs/codex/PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md for proof-class or actual-app-delta questions
- docs/codex/TEST_CLASSIFICATION_LIBRARY.md and docs/codex/VALIDATION_BUCKETS.md for test additions, promotions, demotions, or retirements
- docs/codex/CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md only for legacy Controller-handoff maintenance when explicitly selected

Repository:
C:\Users\aidan\ScryRaven

Start state:
- Start from updated main.
- Confirm main includes the previous merged phase.

Suggested branch:
codex/<phase-branch-name>

Phase-end publication:
- Use docs/codex/CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md.
- Use workspace sandbox for implementation, tests, inspection, and file edits.
- For Git metadata or publication, request approval for the exact command only.
- After implementation, tests, and self-review, exact-approved commands may push the completed phase branch and create a pull request into main.
- Do not merge, squash, rebase, force-push, delete branches, reset, clean destructively, or alter main.

Primary outcome:
<One sentence: what this phase must accomplish.>

Mode:
BUILD | PROOF | REPAIR

Usable-answer verdict target:
YES | NO-BUT-JUSTIFIED

Build / Proof / Repair approval standard:
- BUILD is the default and must move ScryRaven closer to answering real user
  questions; the usable-answer verdict target is YES.
- PROOF is an explicit exception to reduce uncertainty before Build work; the
  usable-answer verdict target is NO-BUT-JUSTIFIED, with a mandatory next Build
  checkpoint and proof-only/non-claim boundaries.
- REPAIR fixes a named integrity defect in a product-moving path or in the
  repo-doc operating system. Product-path repair targets YES; repo-doc/process
  repair may target NO-BUT-JUSTIFIED only when it names the product-moving
  failure prevented and the next Build/product checkpoint protected.
- Current repo-doc posture: after #352 through #355, the next gate is tightly
  scoped limited live validation, not another proof layer.

Skeptical outside-reviewer question:
Is this finally building the app, or is it building convincing apparatus around the app?

A phase brief is invalid if a skeptical reviewer could fairly describe the
deliverable as "a nice collection of harnesses" and the ordinary product path
still cannot demonstrate the claimed behavior.

Required proof, product, and validation posture:
Proof class:
Product-facing progress type:
Product path affected:
Runtime consumer:
Actual consumer seam:
Actual app delta:
User-facing/reviewable output delta:
Non-product exception leash:
Mandatory next product-path checkpoint:
Existing machinery reused:
New machinery introduced:
Why this is not reinventing an existing surface:
Old path treatment:
Human-reviewable product output:
Validation bucket:
Test classification / promotion posture:
New tests:
Fast_pr promotion rationale, if any:
Non-proofs:
Live validation status:
Bridge or exit condition:

For BUILD or product-facing REPAIR phases, also fill in:
Ordinary entrypoint:
User-style demonstration input:
Forbidden substitute outputs:
- harness-only path
- fixture-only path
- proof-only script
- replay-only path
- packet-only artifact
- projection-only artifact
- docs-only doctrine
- shadow vertical slice
Product-path pass condition:
A user-style input enters through the ordinary product/CLI/app path and produces the claimed reviewable output.
Product-path fail condition:
The ordinary product path cannot consume the change. Stop with a blocker report instead of demonstrating the behavior beside the product.

Product-facing progress type must be one of:
- product-path integration
- product-facing dry-run/dogfood output
- quarantine/docs-process work
- fixture-only proof with explicit product-path leash
- offline harness proof with explicit product-path leash
- live-search-only validation with explicit live license
- live product proof with explicit live license

For any non-product phase, fill in the non-product exception leash. It must name
why product-path work is not licensed or safe in this phase, the current path
consumer or blocker being clarified/removed, the mandatory next product-path
checkpoint, existing machinery reused, any new machinery introduced, why the work
is not reinventing an existing surface, and the exact non-proofs.

Harness/proof-only/replay-path requirement:
Every new harness, proof-only script, replay path, packet-only demo, or
non-product scaffold must fill in:
Harness label:
PRODUCT-PATH-REGRESSION | SEAM-DIAGNOSTIC | INTEGRATION-STAGING | EXPLORATORY-PROOF-ONLY | SHADOW-PRODUCT-HARNESS
Ordinary product path guarded or fed:
Runtime consumer:
Why ordinary product-path work cannot be done directly:
Integration deadline:
Exit condition:
Why this is not a shadow product path:
Forbidden interpretation:

Harness expiration:
A harness created in phase N should be consumed, converted to a product-path
regression guard, deleted, or marked historical/proof-only debt by phase N+1. It
may survive to N+2 only if N+1 exposed a specific blocker and N+2 is explicitly
the integration/retirement phase. After N+2, unconsumed harness/proof scaffolding
is historical/proof-only debt by default and must not be cited as product
progress.

Surface vocabulary:
- licensed surface = explicitly opened by the phase brief
- target surface = the thing this phase is meant to inspect/change/reduce/retire
- high-custody surface = important/risky behavior requiring narrow scope, tests, and stop conditions
- closed-this-phase surface = do not touch in this phase
- historical surface = retained as record, not current doctrine or product path
- strangler target = reduce, bypass, demote, subordinate, or delete over time
- protected is retired as active phase-control vocabulary

Current authority/product-consumed vocabulary:
- current internal authority path = canonically owned/reduced internally, not necessarily product-visible
- current product-consumed path = ordinary CLI/app/product flow consumes it
- fixture-only proof = fixture-backed seam proof, not product-consumed
- offline harness / proof-only harness = offline scaffold/script, not product-consumed unless ordinary path consumes it
- integration-staging harness = temporary scaffold while wiring a named product consumer
- product-facing dry-run proof = reviewable dry-run output, not live product correctness
- historical/proof-only debt = retained proof history that must not be cited as product progress

New tests must be classified before being added to permanent bucket manifests.

Compact validation plan:
- Exact bucket command(s):
  ...
- Exact phase_focus test path(s) or node id(s):
  ...
- Full offline required:
  yes | no, because ...
- Intentionally not run:
  ...
- Collection/timing note needed:
  yes | no, because ...

Rule 0 failure_analysis:
- General failure class:
  ...
- Blast radius:
  ...
- Rules that apply:
  ...
- Valid cases this could accidentally block/degrade:
  ...
- Telemetry/process signals:
  ...
- Simplest positive test:
  ...
- Simplest negative-control test:
  ...

In scope:
- ...

Autonomy / decision-point policy:
- Proceed autonomously for relevant file inspection, scoped implementation, in-scope tests, in-scope test fixes, docs cross-link fixes caused by the phase, formatting/pre-commit fixes, final-bundle preparation, and PR creation when explicitly authorized.
- Stop for product choices, unresolved architecture forks, unlicensed or closed-this-phase surface changes, live validation, secrets/private data, destructive git, merge/rebase/force-push, broad scope expansion, or unresolved failing tests that imply a design decision.

Out of scope:
- live calls unless separately approved
- provider routing changes unless explicitly scoped
- prompt rewrites unless explicitly scoped
- source ranking/filtering changes unless explicitly scoped
- persistence schema changes unless explicitly scoped
- high-custody surface redesign unless explicitly scoped
- destructive git
- merge

Live validation, if approved:
- Live validation is disabled unless this section is explicitly filled in.
- Max live ScryRaven/proplex provider/model/search/fetch/read calls:
  ...
- Exact commands/harness:
  ...
- Decision the live run will make:
  ...
- Committed validation doc path, if any:
  docs/validation/...
- Local output-quality review packet path:
  output/ag##_output_quality_review_packet.md
- Do not call this a truth packet or truth review packet.
- Confirm packet ignored/untracked:
  git check-ignore -v output/ag##_output_quality_review_packet.md
  git ls-files output
- Do not include secrets, raw provider payloads, raw prompts, DB rows, caches, full traces, private logs, or unrelated generated outputs.

Testing expectations:
- Name the required validation tier:
  `docs_only` | `fast_pr` | `phase_focus` | `author_lane` | `full`
- Choose the smallest valid bucket and report the exact command.
- For ordinary PRs, prefer `fast_pr`; do not use `author_lane` or `full` unless
  this phase explicitly licenses it.
- Do not add every new test to `fast_pr`.
- Do not repeatedly rerun monolithic timeouts; split the command or report the
  timeout.
- ruff or touched-file lint/format checks
- diff check
- focused new tests
- relevant existing tests

Final bundle:
Use the final bundle format from docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md.

Return one final phase bundle only after implementation, tests, in-scope fixes,
self-review, and optional phase-end PR creation.
```
