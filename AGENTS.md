# Root AGENTS.md for ScryRaven

Status: Active standing guidance for Codex tasks in this repository. This file is
always loaded; use `docs/codex/CODEX_GUIDANCE_MAP.md` to route to
task-specific guidance.

## Project identity

ScryRaven is the public project name. Historical/internal compatibility names may
remain where already supported: `proplex`, `python -m proplex`, `PROPLEX_*`,
`proplex.db`, and `proplex_*` state keys.

## Repo-doc boundary

Use repo-visible files and the current task prompt. Do not assume ChatGPT Project
Sources are files in this repository unless their content is explicitly provided
or committed here.

## Default safety rules

No live ScryRaven/proplex provider, model, search, or retrieval calls by default.
Do not access secrets, `.env`, API keys, raw provider payloads, raw prompts, DB
rows, private logs, caches, full raw traces, local output packets, or private
artifacts unless a phase explicitly scopes safe redacted access.

## Surface vocabulary

Use current phase-boundary words precisely:

- **target surface** = the thing this phase is meant to inspect, change, reduce,
  move, simplify, retire, or strangle.
- **high-custody surface** = important/risky behavior that may be changed only
  with narrow scope, named tests, and stop conditions.
- **closed-this-phase surface** = do not touch in this phase.
- **historical surface** = retained as record, not current doctrine or product
  path.
- **strangler target** = a surface to reduce, bypass, demote, subordinate, or
  delete over time.
- **licensed surface** = explicitly opened by the phase brief.

"Protected" is retired as active phase-control vocabulary because it can imply
"do not touch." When a surface is important and risky but intended to be changed,
call it a high-custody target or strangler target, not protected.

## Bounded autonomy and escalation

Proceed autonomously for relevant repo inspection, scoped implementation,
in-scope tests, in-scope failure fixes, docs cross-link fixes caused by the
phase, formatting/pre-commit fixes, self-review, final-bundle preparation, and PR
creation when explicitly authorized.

Stop and ask for product choices, unresolved architecture forks, unlicensed or
closed-this-phase surface changes, live validation, secrets/private data,
destructive git, merge/rebase/force-push, broad scope expansion, or unresolved
failing tests that imply a design decision.

## Product-facing progress default

Default to converting existing machinery into product-path output rather than
adding new fixture/proof/projection layers. Every phase brief and final bundle
should state the product-facing progress type, the actual user-facing or
reviewable output delta, the actual consumer seam, existing machinery reused,
new machinery introduced, old path treatment, and why the work is not
reinventing an existing surface.

Non-product phases are allowed only with an explicit non-product exception
leash. The non-product exception leash must state proof class, reason
product-path work is not licensed or safe in this phase, named blocker or
current-path consumer, mandatory next product-path checkpoint, and explicit
non-proofs. For the current post-#352 through #355 sequence, the mandatory next
product checkpoint is tightly scoped limited live validation, not another proof
layer or fixture dogfood checkpoint.

Stop if actual app delta is vague, if a new harness/proof/packet/projection is
proposed without a named current-path consumer or blocker removal, or if fixture
or offline proof is being described as product correctness, live product
validation, citation rendering, source-obligation satisfaction, or
AuthorProse product proof.

Skeptical outside-reviewer question:

```text
Is this finally building the app, or is it building convincing apparatus around the app?
```

A phase brief is invalid if a skeptical reviewer could fairly describe the
deliverable as "a nice collection of harnesses" and the ordinary product path
still cannot demonstrate the claimed behavior.

## Phase mode gate

Build / Proof / Repair is the active phase operating system. Every phase must
declare exactly one mode:

```text
Mode: BUILD | PROOF | REPAIR
```

"Prove Mode" is retired as a global workflow label. Proof is only a phase mode
under Build / Proof / Repair, and it is an exception with a leash, non-claims, a
named blocker, and a mandatory next Build/product checkpoint.

BUILD is the default. A Build phase must move ScryRaven closer to answering real
user questions, target a usable-answer verdict of YES, and produce a user-style
input, local command, API path, app path, reviewable answer artifact, answer
output behavior, product-path repair, or legacy-path deletion/quarantine that
affects the user-answer flow. A Build PR may cross multiple internal seams when
that is the smallest useful vertical slice.

PROOF is an explicit exception. It must target NO-BUT-JUSTIFIED, answer a named
technical question that blocks Build work, carry the non-product exception leash,
state what cannot be claimed, identify throwaway/fixture/proof-only code, and
name a mandatory next Build checkpoint. No second Proof phase for the same
blocker is allowed without explicit user approval.

REPAIR fixes a named integrity defect in a product-moving path or in this
repo-doc operating system. Product-path repair should target YES. Repo-doc or
process repair may target NO-BUT-JUSTIFIED only when it names the
product-moving failure it prevents and the next Build/product checkpoint it
protects. Repair work should remove the defect, add a practical regression
guard, make the path or operating system more honest, and avoid broad cleanup or
new architecture.

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

Required fields for any new harness/proof-only script/replay path:

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

## Local Codex publication model

The normal sandbox may keep `.git/` and GitHub authentication protected. Do
implementation, tests, formatting, and self-review inside the normal sandbox.

When a phase explicitly authorizes publication, request at most one final
escalation for `git add`, `git commit`, `git push`, and `gh pr create`. If Git or
GitHub authentication is blocked, stop and report the exact blocker plus the
commands the user can run to clear it.

## Long-phase and goal-mode workflow

For multi-step phases, prefer `/goal` or maintain an explicit checklist. Continue
until the phase goal is complete, tests hit a real blocker, or a stop condition
is reached.

Do not ask for permission for ordinary scoped repo inspection, in-scope edits,
targeted tests, formatting fixes, or self-review. Ask for product choices,
unlicensed surfaces, live calls, secrets/private data, destructive Git,
merge/rebase/force-push, or final Git publication if escalation is required.

## Clean as you cook

Every implementation phase should attempt one adjacent cleanup near the touched
surface. Acceptable cleanup includes deleting, demoting, or consolidating stale
helpers, obsolete imports, misleading comments, duplicate fixtures, or superseded
docs.

Unacceptable cleanup includes adding a new abstraction, projection, lifecycle, or
guard; broad unrelated refactors; or behavior changes outside scope. Final
bundles should report whether cleanup was attempted, what changed, the net line
impact when practical, and the blocker if no safe cleanup was available.

## AG-89+ authority-collapse rule

For AG-89+ work, authority-collapse success requires the intended runtime
consumer to consume the new authority and the old authority path to be deleted,
demoted, bypassed, subordinated, or scheduled for retirement. Trace-only,
storage-only, wrapper-only, prompt-visible-only, or test-only authority is failure
unless the phase is explicitly passive, docs-only, or instrumentation-only.

## Orchestrator containment

Do not add an orchestrator brain. The orchestrator may coordinate lifecycle flow
and call bounded executors, but governing decisions should live in the accountable
RunAuthority / RunKernel or canonical state path named by the phase.

## Testing and final bundle

Run focused offline checks appropriate to the phase. Do not run live/integration
checks unless explicitly scoped. Final responses should summarize changed files,
checks and results, licensed/closed-this-phase/target surfaces, live-validation
status, PR status, and recommended final action.

## Reasoning posture

Use high diligence. If a Codex Cloud reasoning-effort setting is not visible, do
not claim it was changed; proceed carefully.

## Guidance entry points

- `docs/codex/CODEX_GUIDANCE_MAP.md`
- `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`
- `docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md`
- `docs/codex/PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md`
- `docs/codex/EXECUTION_PLAN_TEMPLATE.md`
- `docs/codex/PHASE_BRIEF_TEMPLATE.md`
- `docs/architecture/AG_CURRENT_PATH_QUARANTINE_01.md`
- `docs/codex/CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md` only for legacy
  Controller-handoff maintenance when explicitly selected
