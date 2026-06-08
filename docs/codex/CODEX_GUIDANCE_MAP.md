# Codex Guidance Map

Status: Recommended entry point for future Codex tasks
Suggested repo path: `docs/codex/CODEX_GUIDANCE_MAP.md`

Use this map to choose the smallest relevant guidance surface before starting a
phase. Do not assume ChatGPT Project Sources are repo files; use repo-visible
files and the current phase prompt.

## Start here for ordinary work

- **Ordinary setup, tests, UI, docs, and bounded implementation:** read
  [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md).
- **Reusable phase prompt shape:** read
  [PHASE_BRIEF_TEMPLATE.md](PHASE_BRIEF_TEMPLATE.md).
- **Developer commands and project overview:** read the repo `README.md`,
  `.github/workflows/ci.yml`, `scripts/check.ps1`, `scripts/test.ps1`,
  `scripts/lint.ps1`, `pytest.ini`, `ruff.toml`, and `.pre-commit-config.yaml`
  as relevant to the task.

## Architecture guidance

- **General architecture workflow and Path B PR process:**
  [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md).
- **AG-89+ RunAuthority / authority-collapse work:**
  [RUNAUTHORITY_IMPLEMENTATION_GUIDE.md](RUNAUTHORITY_IMPLEMENTATION_GUIDE.md).
- **AG-89 architecture inventory and doctrine:** start with
  `docs/architecture/AG89A_RUN_KERNEL_ORCHESTRATOR_RETIREMENT_ACCOUNTABILITY_INVENTORY.md`
  and then read later AG-89 docs relevant to the phase (`AG89B` if present,
  `AG89C`, `AG89D`, `AG89E`).
- **Legacy Controller-handoff maintenance only when explicitly selected:**
  [CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md](CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md).

## Multi-step and bundled phases

- Use [EXECUTION_PLAN_TEMPLATE.md](EXECUTION_PLAN_TEMPLATE.md) when a phase has
  several checkpoints, multiple files/seams, runtime consumers, or authority
  paths to delete/demote/bypass/subordinate.
- Use a tiny plan in the final answer or working notes for small one-seam phases.

## Live validation / dogfood

- Live ScryRaven/proplex provider, model, search, or retrieval calls are disabled
  unless the phase explicitly scopes query class, run cap, provider/model/search
  budget, packet path, redaction plan, decision, and stop condition.
- For live validation artifact rules, read the live-validation section in
  [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md).

## PR and final-bundle review

- Use the Path B, bounded-autonomy, protected-surface, and final-bundle sections
  in [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md).
- If the phase is AG-89+ authority-collapse work, also include the final bundle
  fields from [RUNAUTHORITY_IMPLEMENTATION_GUIDE.md](RUNAUTHORITY_IMPLEMENTATION_GUIDE.md).

## Stale-guidance questions

When guidance conflicts:

1. Direct system/developer/user instructions win.
2. The current phase prompt wins over older docs.
3. For AG-89+ authority-collapse, the RunAuthority guide wins over the legacy
   Controller passive-contract ladder.
4. For legacy Controller-handoff maintenance explicitly selected by a phase, the
   Controller playbook may be used within its stated scope.
5. If a conflict would require a product choice, unresolved architecture fork,
   unlicensed protected-surface change, live validation, secrets/private data, or
   destructive git, stop and ask.

## Bounded-autonomy policy summary

Proceed autonomously for relevant inspection, scoped implementation, in-scope
tests, in-scope test fixes, docs cross-link fixes caused by the phase,
formatting/pre-commit fixes, final-bundle preparation, and PR creation when the
phase brief explicitly authorizes it.

Stop for product choices, unresolved architecture forks, unlicensed protected
surfaces, live validation, secrets/private data, destructive git,
merge/rebase/force-push, broad scope expansion, or unresolved failing tests that
imply a design decision.
