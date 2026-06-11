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

Safety-sensitive surfaces are high-custody and phase-bounded, not sacred. Treat
surfaces as licensed when the phase explicitly opens them, closed when the phase
keeps them out of scope, target surfaces when they are intentionally being
strangled or simplified, and historical surfaces when they are retained as
record rather than current doctrine.

## Bounded autonomy and escalation

Proceed autonomously for relevant repo inspection, scoped implementation,
in-scope tests, in-scope failure fixes, docs cross-link fixes caused by the
phase, formatting/pre-commit fixes, self-review, final-bundle preparation, and PR
creation when explicitly authorized.

Stop and ask for product choices, unresolved architecture forks, unlicensed or
closed-surface changes, live validation, secrets/private data, destructive git,
merge/rebase/force-push, broad scope expansion, or unresolved failing tests that
imply a design decision.

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
checks and results, licensed/closed/target surfaces, live-validation status, PR
status, and recommended final action.

## Reasoning posture

Use high diligence. If a Codex Cloud reasoning-effort setting is not visible, do
not claim it was changed; proceed carefully.

## Guidance entry points

- `docs/codex/CODEX_GUIDANCE_MAP.md`
- `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`
- `docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md`
- `docs/codex/EXECUTION_PLAN_TEMPLATE.md`
- `docs/codex/PHASE_BRIEF_TEMPLATE.md`
- `docs/codex/CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md` only for legacy
  Controller-handoff maintenance when explicitly selected
