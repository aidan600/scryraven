# Codex Guidance Map

Status: Task-specific routing map for future Codex tasks
Suggested repo path: `docs/codex/CODEX_GUIDANCE_MAP.md`

Repo-root `AGENTS.md` is the always-loaded standing instruction file for
ScryRaven tasks. Use this map to choose the smallest relevant task-specific
guidance surface before starting a phase. Do not assume ChatGPT Project Sources
are repo files; use repo-visible files and the current phase prompt.

## Start here for ordinary work

- **Ordinary setup, tests, UI, docs, and bounded implementation:** read
  [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md).
- **Reusable phase prompt shape:** read
  [PHASE_BRIEF_TEMPLATE.md](PHASE_BRIEF_TEMPLATE.md).
- **Local Windows sandbox and publication rule:** read
  [CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md](CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md).
  Codex edits and tests in the workspace sandbox; exact-approved Git commands
  publish.
- **Proof class and actual app delta questions:** read
  [PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md](PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md).
- **Validation buckets, high-custody tiers, and timeout reporting:** read
  [VALIDATION_BUCKETS.md](VALIDATION_BUCKETS.md) and
  [CI_VALIDATION_ERGONOMICS.md](CI_VALIDATION_ERGONOMICS.md). Choose the
  smallest valid bucket, report the exact command, and do not run full pytest
  unless the phase requires it.
- **Test additions, promotions, demotions, or retirements:** read
  [TEST_CLASSIFICATION_LIBRARY.md](TEST_CLASSIFICATION_LIBRARY.md) and
  [VALIDATION_BUCKETS.md](VALIDATION_BUCKETS.md). Classify new tests before
  adding them to permanent bucket manifests.
- **Developer commands and project overview:** read the repo `README.md`,
  `.github/workflows/ci.yml`, `scripts/check.ps1`, `scripts/test.ps1`,
  `scripts/lint.ps1`, `pytest.ini`, `ruff.toml`, and `.pre-commit-config.yaml`
  as relevant to the task.

## Architecture guidance

- **General architecural workflow and Path B PR process:**
  [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md).
- **Current AG-SEM posture:** AG-SEM-01 and AG-SEM-02 are merged. AG-SEM-03
  `ComponentCoverageRecord` schema is the next likely passive semantic phase.
  Name the proof class and validation bucket before implementation. For
  historical AG-96 context, read
  `docs/architecture/AG96_CURRENT_STATE_AND_NEXT_CHOICES.md`.
- **AG-89+ RunAuthority / authority-collapse work:**
  [RUNAUTHORITY_IMPLEMENTATION_GUIDE.md](RUNAUTHORITY_IMPLEMENTATION_GUIDE.md).
- **Current source-class recovery dispatch doctrine:** use
  `docs/architecture/AG95C_CANONICAL_RECOVERY_PERMISSION_DISPATCH_CONSOLIDATION.md`,
  `docs/architecture/AG95D_RECOVERY_DISPATCH_SANITY_AUDIT_AND_CLEANUP_TARGET_SWEEP.md`,
  `docs/architecture/AG95E_STALE_DISPATCH_DOCTRINE_AND_FIXTURE_CLEANUP.md`,
  `docs/architecture/AG95F_CONTROLLER_LOOP_SPINE_SOURCE_CLASS_TRACE_DEMOTION.md`,
  `docs/architecture/AG95G_SOURCE_CLASS_COMPATIBILITY_CONSUMER_AUDIT_AND_RETIREMENT.md`,
  `docs/architecture/AG95H_REMAINING_SOURCE_CLASS_COMPATIBILITY_TRACE_DIET.md`,
  and
  `docs/architecture/AG95I_CONTROLLER_LOOP_SPINE_PACKET_FIELD_DIET.md`,
  followed by
  `docs/architecture/AG95J_K_ACTIVE_GATE_AND_LIFECYCLE_BOOLEAN_DIET.md`,
  followed by
  `docs/architecture/AG95L_PIPELINE_PRODUCT_CALLSITE_COMPATIBILITY_READ_DIET.md`,
  `docs/architecture/AG95M_PIPELINE_ORCHESTRATOR_SOURCE_CLASS_AUTHORITY_HELPER_EXTRACTION.md`,
  `docs/architecture/AG95N_O_P_FINAL_AUTHORITY_VISIBILITY_RECOVERY_DECISION_PROJECTION_BURNDOWN.md`,
  and
  `docs/architecture/AG95Q_PROVIDER_REVIEW_ALLOCATION_BURNDOWN.md`.
  Current runner dispatch authority is canonical
  `authority_lifecycle.recovery_action` consumed by
  `SourceClassRecoveryRunner`; `authorized_spine_action`,
  ControllerRecoveryDecision, and ControllerLoopSpine shared active-gate fields
  are diagnostic/compatibility surfaces for source-class dispatch. AG-95I is
  the current ControllerLoopSpine packet-field diet: it retires the
  source-class-specific packet aliases/markers and leaves only shared
  active-gate compatibility where weak-corpus, conflict, terminal-stop, or
  targeted-retrieval coverage still needs it. AG-95J/K is the follow-on boolean
  diet: it removes source-class-adjacent shared active-gate assertions and
  rewrites redundant lifecycle/admission booleans to canonical
  AuthorityLifecycle recovery-action or runner execution proof. AG-95L/M/N-O-P
  are the current pipeline burn-down chain: L rewrites product callsite reads to
  canonical AuthorityLifecycle action/blocker state, M extracts bounded
  source-class authority reads, N/O/P moves final visibility/citation handoff
  to FinalEvidenceBundle/FinalAnswerPacket observation, and AG-95Q moves
  provider-review allocation runtime ownership to canonical
  RunAuthority/SearchJudgment-fed lifecycle state consumed by the provider
  allocation helper. AG-95R/S/T retires ControllerRecoveryDecision from active
  visibility export; current export coverage observes canonical provider-review
  allocation fields. AG-95F/G/H
  are historical setup phases; use AG-95I through AG-95Q for the current packet,
  lifecycle, provider-review allocation, and pipeline product-callsite
  compatibility contract.
- **Orchestrator strangulation and phase-boundary vocabulary:** read
  `docs/architecture/AG94G_ORCHESTRATOR_AUTHORITY_STRANGLER_MAP.md` after the
  RunAuthority guide when a phase touches `core/pipeline_orchestrator.py`,
  controller/orchestrator cleanup, or the licensed/closed/target/historical
  surface vocabulary.
- **Current authority doctrine / stale Controller vocabulary audit:** read
  `docs/architecture/AG94C_AUTHORITY_DOCTRINE_DETRITUS_AUDIT.md` after the
  RunAuthority guide when a phase touches authority, projection/export/report
  meaning, controller/orchestrator cleanup, or naming debt.
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

- Use the Path B, bounded-autonomy, surface-boundary, and final-bundle sections
  in [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md).
- If the phase is AG-89+ authority-collapse work, also include the final bundle
  fields from [RUNAUTHORITY_IMPLEMENTATION_GUIDE.md](RUNAUTHORITY_IMPLEMENTATION_GUIDE.md).
- Always report the validation bucket used. For PRs, `fast_pr` is the normal
  non-docs target unless the phase explicitly licenses `author_lane` or `full`.

## Surface Boundary Vocabulary

Use precise phase-boundary words in current prompts and reviews:

- **Licensed surface:** a file, module, behavior, or document the current phase
  explicitly allows Codex to inspect or change.
- **Closed surface:** a surface kept out of scope for this phase.
- **Target surface:** a surface intentionally being reduced, moved, simplified,
  or retired over time.
- **Historical surface:** retained as project history, not current doctrine.
- **Safety-sensitive surface:** high-custody behavior such as provider routing,
  prompt semantics, citation behavior, persistence shape, or live validation.

The legacy word "protected" should not mean sacred. For
`core/pipeline_orchestrator.py`, "line delta: 0" is only a scope-control fact.
It is not architecture success. In ordinary product behavior phases the
orchestrator may be closed for safety; in orchestrator-strangulation phases it
is a target surface.

## Stale-guidance questions

When guidance conflicts:

1. Direct system/developer/user instructions win.
2. The current phase prompt wins over older docs.
3. For AG-89+ authority-collapse, the RunAuthority guide wins over the legacy
   Controller passive-contract ladder.
4. For current-looking architecture summaries that still say "Controller
   decides, orchestrator executes", prefer the AG-94C authority doctrine audit
   and this map's AG-95 source-class dispatch routing. Treat older summaries as
   historical unless a phase explicitly refreshes them.
5. For legacy Controller-handoff maintenance explicitly selected by a phase, the
   Controller playbook may be used within its stated scope.
6. If a conflict would require a product choice, unresolved architecture fork,
   unlicensed or closed-surface change, live validation, secrets/private data,
   or destructive git, stop and ask.

## Bounded-autonomy policy summary

Proceed autonomously for relevant inspection, scoped implementation, in-scope
tests, in-scope test fixes, docs cross-link fixes caused by the phase,
formatting/pre-commit fixes, final-bundle preparation, and PR creation when the
phase brief explicitly authorizes it.

Stop for product choices, unresolved architecture forks, unlicensed or closed
surfaces, live validation, secrets/private data, destructive git,
merge/rebase/force-push, broad scope expansion, or unresolved failing tests that
imply a design decision.
