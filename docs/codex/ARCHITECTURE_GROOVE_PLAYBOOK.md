# ScryRaven Build / Proof / Repair Playbook

Status: Recommended repo-tracked playbook for product-engineering phases.
Suggested repo path: `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`

Historical note: this file used to be titled Architecture Groove / Prove Codex
Playbook. That phrase is retired as active workflow language. Build / Proof /
Repair is the active phase operating system.

## Purpose

This playbook owns detailed workflow rules for ScryRaven coding-agent phases.
Future phase prompts should be short and should reference this playbook, the
[Codex Guidance Map](CODEX_GUIDANCE_MAP.md), and any phase-specific guide rather
than re-stating the whole operating manual.

The root `AGENTS.md` owns durable safety, human-authority, product-path, Git, and
publication boundaries. [AGENTIC_CODING_OPERATING_PROFILE.md](AGENTIC_CODING_OPERATING_PROFILE.md)
owns vendor-neutral execution profiles and the advisory current Codex adapter.

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
3. Inspect and plan the bounded implementation.
4. Implement with narrow continuation checks while one causal cluster converges.
5. At a coherent checkpoint, run phase-focus and immediate-owner proof.
6. Create coherent milestone commits and one clean candidate checkpoint.
7. Review the exact implementation diff and run the local final-candidate checks once.
8. If authorized, push and update or open the PR, then wait for exact-head hosted CI.
9. If separately authorized, run exceptional broad validation as its own job.
10. Perform final independent or skeptical-maintainer review.
11. Return one final phase bundle.
```

Final-candidate validation is one checkpoint completed across the local checks
in step 7 and exact-head hosted CI in step 8; publication does not restart the
validation bundle.

GitHub is the review surface for a completed phase branch, not a sub-step
synchronization layer. Codex must not merge the PR.

Use the canonical [Review-Loop Validation Ramp](VALIDATION_BUCKETS.md#review-loop-validation-ramp)
for continuation, coherent-checkpoint, and final-candidate routing. A review
verdict B defaults to its narrow continuation posture; do not rerun the complete
phase bundle unless the correction meets a documented broader-validation
condition.

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

A PR may be large when it implements one coherent product outcome through its
ordinary consumer. Do not split solely because the outcome crosses several
files, modules, authority seams, or internal implementation milestones.

Split when the work contains independent product decisions, unrelated
consumers, materially different risk classes, or incompatible rollback
boundaries. Small PRs remain valid and desirable when they are the natural
coherent unit. Pick the smallest phase shape that completes the outcome without
creating avoidable user coordination work or an unusable partial path.

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

## Long-running task contract

For substantial work, express the contract as:

```text
Outcome:
Constraints:
Verification:
```

The agent should inspect the repository, form a compact internal plan, and
proceed through related internal milestones without waiting for approval. Use
checkpoint commits when useful. Run focused validation during implementation,
complete the ordinary consumer endpoint, review the complete diff, fix in-scope
findings, rerun affected validation, and return one final bundle.

Internal milestones are coordination aids, not automatic PR boundaries. Use
coherent local checkpoint commits at completed seams and before expensive
validation. When blocked, leave a clean worktree at the last coherent checkpoint
or only the exact explicitly reported unresolved edit. Checkpointing does not
claim completion, correctness, publication permission, merge approval, or broad
validation success. Stop only at divergence, unrelated responsibility,
architectural uncertainty, the decision and authority boundaries in the root
contract, or a phase-specific stop condition—not merely because focused tests
remain red while the same causal cluster is shrinking and directly implies the
next bounded correction.

## Implementation and validation jobs

Keep implementation, affected-lane validation, publication, full-suite or
baseline-parity validation, and final review as separate jobs. Implementation
context is for building and focused correction; affected lanes establish
confidence in directly owned integration surfaces. Broad validation classifies
repository behavior and may block merge, but must not strand a coherent
implementation as uncommitted work.

When broad validation is red, capture exact failures and do not immediately
repeat the broad run. Diagnose with focused tests or owning lanes, repair
branch-attributable failures, create a new coherent checkpoint when needed, and
then run at most the authorized final broad validation. Do not rerun the full
suite after every isolated correction or run multiple broad validation processes
concurrently. Record why each broad run was authorized, report only meaningful
state changes, and infer neither success nor failure from silence or elapsed
time. A separate broad job need not stop productive work that does not invalidate
its candidate checkpoint.

## Stable acceptance ownership

One Strategy/Review chat owns the active phase acceptance target. Gather
material red-team findings before the phase brief and queue noncritical new ideas
for later. Interrupt implementation only for immediate safety, authority, or
product-integrity blockers. A new observation becomes a mid-phase requirement
only when it exposes authority laundering, unsafe secret/private-data exposure,
behavior contrary to the approved product thesis, or a genuine architecture
decision. Review chooses exactly one: approve merge, request one focused fix,
reject or revert, or stop for architectural decision.

## Adjacent cleanup

Implementation phases should attempt one safe cleanup near the touched surface:
delete, demote, or consolidate a stale helper, obsolete import, misleading
comment, duplicate fixture, or superseded instruction. Do not use cleanup to add
a new abstraction or lifecycle, broaden the refactor, or change unrelated
behavior. Report the cleanup or the reason none was safe.

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

### Temporal truth ownership

Current installed state is owned by
`docs/architecture/SCRYRAVEN_CURRENT_STATE.md`. Current phase sequence is owned
by `docs/roadmap/CURRENT_ROADMAP.md`. The canonical deep multi-component
architecture remains
`docs/architecture/MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md`.

This playbook owns workflow, not the product roadmap. Phase briefs must route to
the temporal owners and must not copy completed-phase chronology into durable
workflow guidance.

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

Recent generic single-relation dogfood, planning, and acquisition work is also
a mature capability surface. Future phases touching query planning, acquisition
planning, FastModel/SmartModel routing, provider acquisition/extraction,
fetch/read, candidate/window selection, source gateway, readiness, or generic
dogfood output must inventory the shared model-assisted single-relation
planning, strict accounted FastModel planning route, OpenAI Responses-backed
FastModel route for OpenAI, product-owned provider acquisition/extraction,
answer-bearing candidate/window selection diagnostics, source/readiness
gateway, and generic dogfood D-prime authority integration blocker before
adding new modules or replacement seams. Prefer `REUSE` / `ADAPT` / `UPGRADE`
over parallel replacement; `REPLACE` requires a reason and an exit plan for the
old surface.

## Hosted and local validation roles

### Hosted implementation role

A hosted coding agent should inspect repo-visible files, plan briefly, execute scoped work,
add or update in-scope tests/docs, run focused offline checks, fix in-scope
failures, self-review, and open a PR when explicitly authorized.

### Local desktop validation / dogfood role

Local desktop validation is for user-run app review, secrets-backed live calls,
private artifacts, DB inspection, caches, local packets, and output-quality
judgment. A coding agent must not assume those artifacts are repo files or
request them unless the phase explicitly scopes safe redacted access.

## Bounded autonomy and decision points

Use the autonomy and escalation boundary in root `AGENTS.md`. The phase brief
may narrow that authority but does not need to repeat it. Do not stop for issues
that are safely fixable within the licensed phase scope.

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

## Required implementation and review loop

For substantial BUILD phases:

1. Complete the full scoped product outcome.
2. Run focused checks.
3. Run required broader regression checks.
4. Review the entire branch diff against `main`.
5. Check correctness, authority boundaries, regressions, unnecessary machinery,
   stale-path retirement, security, and private-data exposure.
6. Fix all in-scope findings.
7. Rerun affected checks.
8. Perform one final skeptical-maintainer review.
9. Report unresolved risks and nonproofs.

A read-only independent reviewer may be used at DEEP, INTENSIVE, or DELEGATED
profiles. The main agent remains the sole architectural integrator and default
writer; delegation begins with read-heavy exploration, testing, triage,
summarization, or independent review. Parallel edits to overlapping files are
forbidden. See `AGENTIC_CODING_OPERATING_PROFILE.md`.

## Final bundle

Use this compact default:

```text
1. Outcome and scope
2. Material changes
3. Verification evidence
4. Self-review findings and fixes
5. Risks and nonproofs
6. Git/PR status
7. Recommended next action
```

Add phase-specific appendices only when they apply, such as authority migration,
live validation, harness retirement, or detailed publication evidence.

## Phase-end PR creation

If the phase brief says phase-end publication is allowed:

```text
After tests and self-review, Codex may push the completed branch and create a PR into main.
Codex must not merge.
```
