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
  unless the phase requires it. Use `semantic_lane` for durable semantic
  producer/reducer/sufficiency validation and `semantic_search_lane` for
  SearchJudgment/QueryPlan semantic-gap consumer validation.
- **Test additions, promotions, demotions, or retirements:** read
  [TEST_CLASSIFICATION_LIBRARY.md](TEST_CLASSIFICATION_LIBRARY.md) and
  [VALIDATION_BUCKETS.md](VALIDATION_BUCKETS.md). Classify new tests before
  adding them to permanent bucket manifests.
- **Developer commands and project overview:** read the repo `README.md`,
  `.github/workflows/ci.yml`, `scripts/check.ps1`, `scripts/test.ps1`,
  `scripts/lint.ps1`, `pytest.ini`, `ruff.toml`, and `.pre-commit-config.yaml`
  as relevant to the task.

## Current Productization Posture

ScryRaven is post-PR #323 / post-AG-OFFLINE-XAXIS-E2E-01. The completed
baseline includes guarded blocked FinalAnswerPacket input derivation, safe
blocked-FAP failure summaries, component-level blocked-FAP summary telemetry, an
offline ComponentPlan / component executor contract, a RunKernel-owned passive
AnswerContractAuthorityMap, completed ComponentSearchPlan naming / subordination
cleanup, the offline RunKernel-owned SearchExecutor bridge, EvidenceLedger
component-scoped source custody, component evidence/citation binding,
SufficiencyJudgment / FinalAnswerPacket component readiness, and an offline
X-axis end-to-end proof through blocked FAP / Author handoff.

The completed Offline SearchExecutor bridge is offline and inert, does not
perform live provider/search/fetch/read/retrieval work, does not admit
EvidenceLedger custody or satisfy source obligations, keeps candidate
observations non-evidence, and is not user-facing runtime search. PR #320 /
AG-COMPONENT-SCOPED-SOURCE-CUSTODY-01 adds EvidenceLedger component-scoped
source custody from that bridge output: component source requirements, candidate
links, custody gaps, and unsatisfied/pending source-obligation state. Candidate
links remain non-evidence until fetched, read, and admitted by a later phase,
and source obligations are unsatisfied/pending rather than satisfied by
candidate presence. PR #321 / AG-COMPONENT-EVIDENCE-CITATION-BINDING-01
completed the component evidence/citation binding phase: it extends the
existing AnswerContractAuthorityMap per-component binding status so it consumes
EvidenceLedger component-scoped custody, preserves candidate links and custody
gaps as component-specific blockers, and keeps custody/candidate presence
non-binding. PR #322 / AG-SUFFICIENCY-FAP-COMPONENT-READINESS-01 completed
existing SufficiencyJudgment and FinalAnswerPacket consumption of those passive
binding/custody inputs into component-aware blocked readiness. PR #323 /
AG-OFFLINE-XAXIS-E2E-01 adds the offline X-axis end-to-end proof through blocked
FAP / Author handoff. It does not enable partial answers and does not enable
live validation.

RunKernel / RunAuthority remains the root authority. AnswerContractAuthorityMap
owns the answer-component authority mapping. ComponentPlan is legacy/compat
input terminology for subordinate component-search planning; ComponentSearchPlan
is the preferred subordinate name. ComponentPlan, ComponentSearchPlan,
SearchWork, QueryPlan, and SearchExecutor are work-description or execution
surfaces only; they do not decide answerability, source-obligation
satisfaction, final readiness, citation eligibility, or Author handoff.

The immediate current doctrine is the integrated run-contract semantic loop:
semantic producer / planner understands, RunKernel governs, AnswerContract
records obligations and statuses, workers propose observations or amendments,
RunKernel validates/reduces, EvidenceLedger records custody, SemanticObservation
records evidence-relative meaning, ComponentCoverage records component support,
SufficiencyJudgment decides readiness, FinalAnswerPacket packages Author-safe
handoff, and Author writes prose only. See
`docs/architecture/RUN_CONTRACT_SEMANTIC_LOOP.md` and
`docs/architecture/AG_ANSWER_CONTRACT_AUTHORITY_MAP_01_DECISION.md`.

AG-RUN-CONTRACT-MUTATION-LOOP-01 implements RunKernel-owned application of
admitted amendments into `current_answer_contract`.
AG-SEARCH-PLANNER-RUNTIME-01 completes the RunKernel-authorized SearchPlanner
proposal seam: an explicitly injected adapter can produce a passive
QMR-compatible proposal plus subordinate component-search requirements, while
live model/search/fetch/read/retrieval behavior remains closed and amendments
remain deferred. The post-merge next gate is AG-SEARCH-PLANNER-MODEL-01.
Bounded live validation is deferred until the upstream
semantic-contract/planner/scout/search-executor runtime loop exists.
Passive/shadow surfaces are not product readiness.

AG-BAL-HARDEN and the component executor contract are not live validation: live
provider, model, search, fetch, and retrieval calls remain closed by default
unless a phase explicitly scopes the live query class, budget, redaction plan,
artifact path, decision, and stop condition.

Balanced now has a hardened, default-disabled, one-gap / one-query / one-cycle
offline recovery seam. Recovery mechanics are shared primitives; modes supply
policy and budget envelopes. Project Sources are not repo files unless their
content is explicitly pasted into the current prompt or committed here.

## Architecture guidance

- **General architectural workflow and Path B PR process:**
  [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md).
- **Previous AG-SEM posture:** AG-SEM-05 through AG-SEM-10 completed the
  canonical reducer and conditional Sufficiency-consumption chain; AG-SEM-11
  and the later semantic atomicity work moved the ordinary semantic producer
  past the old "next vertical slice" gate. Use
  `docs/architecture/AG_SEM_05_10_COMPLETION_AND_NEXT_GATES.md` as historical
  context, not current next-step doctrine. For historical AG-96 context, read
  `docs/architecture/AG96_CURRENT_STATE_AND_NEXT_CHOICES.md`.
- **Integrated run-contract semantic loop:** read
  `docs/architecture/RUN_CONTRACT_SEMANTIC_LOOP.md` for the current doctrine
  connecting AG-SEM semantic authority to ComponentSearchPlan, Scout,
  SearchExecutor, EvidenceLedger, SufficiencyJudgment, FinalAnswerPacket, and
  prose-only Author handoff. It cross-references the relevant AG-SEM records:
  `AG_SEM_01_PASSIVE_SEMANTIC_CONTRACT_FOUNDATION.md`,
  `AG_SEM_02_SANITIZED_CONTENT_REFERENCE_AND_SEMANTIC_OBSERVATION.md`,
  `AG_SEM_04_CONTRACT_AMENDMENT_RECORD.md`,
  `AG_SEM_05_INITIAL_ANSWER_CONTRACT_ACCEPTANCE.md`,
  `AG_SEM_07_COMPONENT_COVERAGE_REDUCTION.md`,
  `AG_SEM_08_CONTRACT_AMENDMENT_ADMISSION.md`,
  `AG_SEM_09_SUFFICIENCY_SEMANTIC_CONSUMPTION.md`,
  `AG_SEM_11_ORDINARY_SEMANTIC_PRODUCER_VERTICAL_SLICE.md`, and
  `AG_SEM_11B_ORDINARY_SEMANTIC_PRODUCER_HARDENING.md`.
- **Recovery-adjacent Balanced / AG-BAL-HARDEN work:** read
  `core/component_gap_recovery_runtime.py`,
  `core/component_gap_recovery_coordinator.py`,
  `core/run_kernel.py` around `commit_recovered_semantic_delta`,
  `core/run_config.py` around `compose_component_gap_recovery_deps`,
  `tests/test_ag_bal_01_component_gap_recovery.py`, and the durable
  `tests/buckets/semantic_search_lane.txt` and
  `tests/buckets/author_lane.txt` manifests. Keep product runtime live calls
  closed by default. Use `semantic_search_lane` for durable QueryPlan/
  SearchJudgment recovery-path proof and `author_lane` for recovered
  fact/source Author-materialization proof when explicitly licensed.
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
- Live multi-component validation is deferred until the upstream
  semantic-contract/planner/scout/search-executor runtime loop exists.
  AG-SEARCH-PLANNER-RUNTIME-01 completes the fail-closed planner proposal
  runtime seam; the immediate next gate is AG-SEARCH-PLANNER-MODEL-01, followed
  by scout, planner-revision, and SearchExecutor handoff phases. For the
  historical AG-LIVE-BOUND-01 preflight
  status and its superseded bridge recommendation, see
  [AG_LIVE_PLAN_01_BOUNDED_LIVE_VALIDATION_PLAN.md](AG_LIVE_PLAN_01_BOUNDED_LIVE_VALIDATION_PLAN.md).
- For live validation artifact rules, read the live-validation section in
  [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md).

## PR and final-bundle review

- Use the Path B, bounded-autonomy, surface-boundary, and final-bundle sections
  in [ARCHITECTURE_GROOVE_PLAYBOOK.md](ARCHITECTURE_GROOVE_PLAYBOOK.md).
- If the phase is AG-89+ authority-collapse work, also include the final bundle
  fields from [RUNAUTHORITY_IMPLEMENTATION_GUIDE.md](RUNAUTHORITY_IMPLEMENTATION_GUIDE.md).
- Always report the validation bucket used. For PRs, `fast_pr` is the normal
  non-docs target unless the phase explicitly licenses `author_lane` or `full`.
- Implementation PR docs should use merge-stable phase posture: previous
  completed baseline, this PR completes/introduces the active phase, and
  post-merge next gate. Do not label the active implementation phase as the
  repo's next/current target in docs updated by that same PR.

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
