# ScryRaven Coding Agent Contract

Status: Active vendor-neutral standing guidance for every repository task.
Use `docs/codex/CODEX_GUIDANCE_MAP.md` to route to task-specific procedures.

## Project and repository boundary

ScryRaven is the public project name. Existing compatibility names such as
`proplex`, `python -m proplex`, `PROPLEX_*`, `proplex.db`, and `proplex_*` state
keys remain supported unless a phase explicitly changes them.

Use repository-visible files and the current task prompt. Do not treat external
project sources or private workspace material as repository files unless their
content is supplied in the prompt or committed here.

## Safety and human authority

No live ScryRaven/proplex provider, model, search, fetch/read, or retrieval call
is authorized by default. Do not access secrets, `.env`, API keys, raw provider
or model payloads, raw prompts, database rows, private logs, caches, full raw
traces, local output packets, or private artifacts unless a phase explicitly
licenses safe, bounded, redacted access.

Proceed autonomously through repository inspection, scoped implementation,
focused offline validation, in-scope fixes, caused cross-link or formatting
repairs, complete-diff review, and final reporting. Stop for a product decision,
unresolved architecture fork, unlicensed or closed surface, live-call authority,
private data, destructive Git, merge/rebase/force-push, broad scope expansion,
or a failing check whose repair would change the phase's meaning.

The human operator selects the actual model and reasoning or intelligence level.
Repository recommendations are advisory and must not force or silently escalate
that selection. Reasoning level never expands scope, permissions, publication
authority, live-call authority, or private-data access.

## Product-path rule

Prefer reuse and ordinary product-path consumption over new parallel machinery.
Before changing a mature capability or authority surface, inventory the current
owner and consumer and classify the intended action as `REUSE`, `ADAPT`,
`UPGRADE`, `RETIRE`, or `REPLACE`. Do not add a shadow answer path, authority,
harness, proof, packet, projection, or registry without a named ordinary
consumer or a named blocker it removes.

Product-facing work must reach the ordinary consumer named by the phase. New
authority is incomplete until that consumer uses it and the old authority is
deleted, demoted, bypassed, subordinated, or explicitly scheduled for
retirement. Trace-, storage-, wrapper-, prompt-, or test-only adoption is not
runtime consumption.

Supported-product evidence sets implementation cadence. No more than three
consecutive merged implementation PRs may produce no supported-product evidence
unless the maintainer explicitly approves an exception naming the blocker and
the next product pulse. After one non-product infrastructure PR, its immediate
successor should consume that infrastructure unless an architectural review
explicitly changes the sequence.

Two failed attempts in the same preparation, authorization, launcher,
workspace, or harness-consumption layer--without reaching the intended product
or component boundary--require architectural review before a third attempt.
Bounded fixes may continue inside one tracked phase while failures remain in one
causal cluster. This rule prevents a third near-identical phase; it does not stop
ordinary in-phase debugging.

Detailed proof classes, harness requirements, and exception leashes are owned by
`docs/codex/PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md` and
`docs/codex/PHASE_BRIEF_ADDENDA.md`.

## Build / Proof / Repair gate

Every phase declares exactly one mode:

```text
Mode: BUILD | PROOF | REPAIR
```

BUILD is the default and delivers a coherent product-moving outcome through an
ordinary user, CLI, API, or app consumer. PROOF is a bounded exception that
answers one named blocker, states nonproofs, and names the mandatory next Build
checkpoint. REPAIR removes a named integrity defect in product behavior or the
repo-visible operating system and adds a practical regression guard when useful.
Repo-doc Repair may target `NO-BUT-JUSTIFIED` only when it identifies the
product-moving failure prevented and the next product checkpoint protected.

## Outcome-based phase sizing

A PR may be large when it implements one coherent product outcome through its
ordinary consumer. Do not split solely because the outcome crosses several
files, modules, authority seams, or internal implementation milestones.

Split when work contains independent product decisions, unrelated consumers,
materially different risk classes, or incompatible rollback boundaries. Small
PRs remain valid and desirable when they are the natural coherent unit.

## Substantial-task contract

Express substantial work as:

```text
Outcome:
Constraints:
Verification:
```

Inspect the repository, form a compact internal plan, and proceed through related
milestones without waiting for approval. During focused implementation, stop on
divergence, unrelated scope expansion, or architectural uncertainty; do not stop
merely because tests remain red while failures decrease within one causal cluster
and the next correction is bounded and directly implied. Create coherent local
checkpoint commits at milestones and before expensive validation. Complete the
ordinary consumer endpoint, review the entire diff against the base, rerun
affected validation, and return one final bundle. Details are owned by the
operating profile and playbook.

The default final bundle is: outcome and scope; material changes; verification
evidence; self-review findings and fixes; risks and nonproofs; Git/PR status; and
recommended next action. Add specialized appendices only when applicable.

## Validation and review

Use the smallest valid offline validation bucket and classify new tests before
adding them to permanent manifests. Do not run live or secrets-backed checks
unless explicitly licensed. Review the complete branch diff for correctness,
authority boundaries, regressions, unnecessary machinery, stale-path retirement,
security, and private-data exposure. Substantial BUILD phases also require the
full implementation and skeptical-maintainer loop in the playbook.

## Git and publication

Preserve user changes and avoid destructive operations. Do not merge, rebase,
force-push, delete branches, destructively clean, or mutate `main`. Commit,
push, or create a pull request only when the phase or user explicitly authorizes
publication. If the known publication path fails, report the exact failure; do
not repair authentication, ACLs, SSH, OAuth, or sandbox configuration during an
implementation phase.

The canonical Windows sandbox and GitHub publication compatibility contract is
`docs/codex/CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md`.

Post-merge local phase cleanup is owned by `scripts/cleanup_merged_phase.py`,
`scripts/cleanup_merged_phase.ps1`, and
`docs/codex/CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md`. Do not reconstruct
merged-phase worktree/branch/phase-root cleanup as an ad-hoc PowerShell sequence.

## Guidance routes

- `docs/codex/CODEX_GUIDANCE_MAP.md` — task-to-owner routing
- `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md` — phase workflow and review loop
- `docs/codex/AGENTIC_CODING_OPERATING_PROFILE.md` — advisory execution profiles
- `docs/codex/PHASE_BRIEF_TEMPLATE.md` — compact phase contract
- `docs/codex/PHASE_BRIEF_ADDENDA.md` — conditional proof/live/harness/migration/delegation fields
- `docs/codex/EXECUTION_PLAN_TEMPLATE.md` — optional multi-milestone plan
- `docs/codex/PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md` — proof/product claims
- `docs/codex/TEST_CLASSIFICATION_LIBRARY.md` and `docs/codex/VALIDATION_BUCKETS.md` — test scope
- `docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md` — RunAuthority migrations
- `docs/architecture/MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md` — current multi-component architecture
