# ScryRaven Docs Inventory And Consolidation Plan

Status: docs inventory and cleanup plan only. No cleanup performed.

Mode: REPAIR

Product-facing progress type: quarantine/docs-process work.

Runtime changes: none. Live calls: none.

## Scope And Method

This report inventories tracked repository documentation using `git ls-files`.
The inventory includes 361 tracked Markdown/rule docs:

| Family | Count | Notes |
| --- | ---: | --- |
| Root and meta docs | 5 | `.cursor/rules/*.mdc`, `.github/pull_request_template.md`, `AGENTS.md`, `README.md`. |
| `docs/codex/` | 13 | Codex operating system, phase templates, validation/test guidance, publication guidance. |
| `docs/architecture/` | 233 | Current contracts plus many historical phase records. |
| `docs/architecture/historical/` | 1 | Controller-era current-state body already moved out of the current-looking file. |
| `docs/validation/` | 81 | Validation notes and output-quality records, mostly phase history. |
| `docs/product/` | 7 | Product design/usage contracts and rubric docs. |
| `docs/operator/` | 2 | Local broker/provider-proxy operator guidance. |
| `docs/evals/` plus `docs/eval_queries.md` | 2 | Evaluation query docs. |
| Retrieval, quantitative, Cursor, and misc docs | 14 | Roadmaps, handoff drafts, review guides, Cursor workflow, source-refresh draft. |
| `outputs/local_only/ag94c_project_source_candidates/` | 3 | Tracked Project Source candidate drafts referenced by AG-94C; not default Codex docs. |

This phase inspected repo-visible tracked files only. The three tracked
`outputs/local_only/ag94c_project_source_candidates/*` files are inventoried as
tracked candidate drafts, but they should not become default Codex context.
AG-94C says they are candidate text for a user to upload through ChatGPT and do
not update ChatGPT memory automatically.

Do not delete yet: this plan intentionally does not delete, move, rename, or
substantially rewrite docs. Cleanup should happen in a later reviewed PR.

## Classification Table

The rows below are disjoint and exhaustive over the 361 tracked docs found by
`git ls-files`. The classification applies to every doc matched by the row.
Concrete evidence is from status lines, purpose sections, or explicit route
sections in the named docs.

| Matched docs | Count | Classification | Evidence and cleanup posture |
| --- | ---: | --- | --- |
| `AGENTS.md` | 1 | Canonical current source of truth | Status says active standing guidance. It defines Build / Proof / Repair, safety, harness labels, publication, and final bundle rules. |
| `README.md` | 1 | Canonical current source of truth | Project overview, commands, and top-level repo map. Read for product identity and developer basics, not architecture authority. |
| `docs/codex/CODEX_GUIDANCE_MAP.md` | 1 | Canonical current source of truth | Routing map for task-specific guidance and current productization posture. |
| `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md` | 1 | Canonical current source of truth | Defines Path B workflow, phase modes, product-path expectations, reuse-first gate, and final bundle. |
| `docs/codex/PHASE_BRIEF_TEMPLATE.md` | 1 | Canonical current source of truth | Reusable phase prompt contract and required fields. |
| `docs/codex/PROOF_CLASS_AND_ACTUAL_APP_DELTA_GATE.md`, `docs/codex/EXECUTION_PLAN_TEMPLATE.md`, `docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md`, `docs/codex/VALIDATION_BUCKETS.md`, `docs/codex/TEST_CLASSIFICATION_LIBRARY.md`, `docs/codex/CI_VALIDATION_ERGONOMICS.md`, `docs/codex/CODEX_LOCAL_WINDOWS_SANDBOX_PUBLICATION_RULE.md`, `docs/codex/AG_DOC_TEST_SANITY_01_VALIDATION_AUDIT.md` | 8 | Current but supporting | Accurate operating references, but not all should be default-read. Read when the phase touches their concern. |
| `docs/codex/CONTROLLER_AUTHORITY_IMPLEMENTATION_PLAYBOOK.md` | 1 | Historical phase note | Guidance map says use only for legacy Controller-handoff maintenance when explicitly selected. |
| `docs/codex/AG_LIVE_PLAN_01_BOUNDED_LIVE_VALIDATION_PLAN.md` | 1 | Historical phase note | Guidance map labels this as historical broad AG-LIVE-BOUND planning, not current live-validation doctrine. |
| `docs/architecture/SCRYRAVEN_CURRENT_STATE.md` | 1 | Canonical current source of truth | Current-state redirect stub; states the old Controller-era body moved to `historical/` and routes to current docs. |
| `docs/architecture/AG_CURRENT_PATH_QUARANTINE_01.md` | 1 | Canonical current source of truth | Current registry for proof class, consumer seams, current/legacy/passive/closed status, and non-proofs. |
| `docs/architecture/RUN_CONTRACT_SEMANTIC_LOOP.md` | 1 | Canonical current source of truth | Current integrated doctrine for SearchPlanner through AuthorProseFinalization and live-validation boundaries. |
| `docs/architecture/DPRIME_ARCHITECTURE.md` | 1 | Canonical current source of truth | Current D-prime authority split, product-consumed status path, allowed/forbidden outputs, and negative controls. |
| `docs/architecture/MVP_SUPPORTED_QUERY_CLASS_BOUNDARY.md` | 1 | Canonical current source of truth | Current supported-query-class boundary and dogfood limits. |
| `docs/architecture/ANALYST_WORKBENCH_FULL_SLICE.md` | 1 | Current but supporting | Current Workbench phase note with proposal-only boundary, but missing newer follow-up/identity contract details listed below. Promote or rewrite in cleanup. |
| Current second-half architecture contracts named by the guidance map: `AG_ANALYST_EVIDENCE_RELATIVE_REPORT_01.md`, `AG_ANALYSIS_GAP_FOLLOWUP_SEARCH_01.md`, `AG_COMPONENT_COVERAGE_RELIABILITY_PROOF_01.md`, `AG_DOC_SEMANTIC_COVERAGE_CHECKPOINT_01.md`, `AG_FOLLOWUP_SEARCH_AUTHORIZATION_REENTRY_01.md`, `AG_SCRUTINEER_REVIEW_01.md`, `AG_SPECIALIST_SOURCE_BOUND_CALCULATION_01.md`, `AG_SUFFICIENCY_PARTIAL_ANSWER_READINESS_01.md`, `AG_FINAL_ANSWER_PACKET_HARDENING_01.md`, `AUTHOR_PROSE_ONLY_FINALIZATION_01.md` | 10 | Current but supporting | These are accurate seam contracts, but Codex should reach them through the guidance map or the smallest relevant phase contract, not default-read all of them. |
| Current live/dry-run/product-path docs under `docs/architecture/AG_LIMITED_LIVE_*`, `AG_LIVE_*`, `AG_ORDINARY_LIVE_*`, `AG_LOCAL_DRYRUN_*`, `AG_FIXTURE_DOGFOOD_*`, and `AG_CHECK_01_*` | 12 | Current but supporting | Useful for live/dry-run/product-path phases. They must not be treated as live correctness proof unless the phase separately licenses live validation. |
| Current supporting architecture contracts not in the default spine: `AG_ANSWER_CONTRACT_AUTHORITY_MAP_01_DECISION.md`, `DPRIME_PRODUCT_MODEL_ROUTE_CONFIG_BOUNDARY.md`, `FAP_AUTHOR_BOUNDARY.md`, `RUNKERNEL_COMPONENT_DAG_CONCURRENCY.md`, `SOURCE_AUTHORITY_POSTURE.md`, `LEGAL_CURRENT_PRIMARY_TRIAGE_L2A.md`, `LEGAL_CURRENT_SOURCE_QUALITY_L2B.md`, `OFFICIAL_NUMERIC_SOURCE_GROUNDING_AG48A.md`, `OFFICIAL_SOURCE_ACQUISITION_SURVIVAL_AG48B.md`, `TARGETED_RETRIEVAL_OWNERSHIP_AG42.md`, `TARGETED_RETRIEVAL_SPINE_REPRESENTATION_AG43C.md`, `TYPED_RETRIEVAL_BATCH_DESIGN_AG46A.md`, and similar narrow contracts | 13 | Current but supporting | Accurate for their seams, but too narrow for default context. Cross-link from the map only when relevant. |
| `docs/architecture/source_hierarchy_answer_contract_invariants.md` | 1 | Stale / contradictory | It states "The Controller and AnswerContract own source-obligation fulfillment." Current doctrine routes authority through RunKernel/RunAuthority plus current D-prime/source-obligation surfaces. Update or mark historical. |
| `docs/architecture/AG51B_*`, `AG74*` through `AG79*`, `AG89*` through `AG95*`, `AG96*`, `ACTIVE_*`, `CONFLICT_*`, `CONTROLLER_*`, `DOCUMENTATION_ROLES_*`, `EVIDENCE_INTEGRATION_*`, `OFFICIAL_*`, `SOURCE_CLASS_*`, `WEAK_CORPUS_*`, and older AG-SEM phase records not named as current contracts above | 191 | Historical phase note | Most are valuable provenance but contain old "Controller-owned", "Architecture Groove / Prove Mode", or phase-local next-gate wording. They should be marked historical or routed through current docs. |
| `docs/architecture/historical/SCRYRAVEN_CURRENT_STATE_CONTROLLER_ERA_HISTORICAL.md` | 1 | Historical phase note | Already has a supersession banner; keep as archive. |
| `docs/validation/*.md` | 81 | Historical phase note | Validation records are phase evidence, not current doctrine. Some live-validation notes are useful provenance, but future phases should not read them by default. |
| `docs/product/*.md` | 7 | Current but supporting | Product rubric/design/usage docs are useful for UX/product phases. They are not core architecture authority unless the phase is product-output-facing. |
| `docs/operator/*.md` | 2 | Current but supporting | Current local broker/provider-proxy operator guidance. Read only when live/provider-proxy work is explicitly licensed. |
| `docs/eval_queries.md`, `docs/evals/reference_query_library.md` | 2 | Current but supporting | Evaluation material and query library. Not architecture doctrine. |
| `.cursor/rules/*.mdc`, `docs/cursor/CURSOR_COMPOSER_WORKFLOW.md` | 3 | Current but supporting | Alternate-agent/editor workflow. Do not use as Codex architecture authority. |
| `.github/pull_request_template.md` | 1 | Current but supporting | PR hygiene only. |
| `docs/MVP_FRIEND_RUNBOOK.md` | 1 | Current but supporting | Useful demo/operator doc; not a claim of arbitrary-query readiness or product correctness. |
| `docs/RETRIEVAL_AND_FAILURE_UX_ROADMAP.md`, `docs/ROADMAP_IMPLEMENTATION_NOTES.md`, `docs/source_refresh_phase14_draft.md`, `docs/phase14_checkpoint_handoff_6f7cc76.md`, `docs/phase15_checkpoint_handoff_5e72fcc.md` | 5 | Historical phase note | Status lines already say historical, superseded, draft, or not active policy. |
| `docs/design_balanced_anchor_resolution_v1.md`, `docs/economist_shadow_telemetry_promotion_policy.md`, `docs/retrieval/*.md`, `docs/quantitative/*.md`, `docs/architecture_safety_contract.md` | 7 | Too detailed for default Codex context | Useful deep context, but should be linked only from relevant phases. Some may later be archived or summarized. |
| `outputs/local_only/ag94c_project_source_candidates/*.md` | 3 | Too detailed for default Codex context | Tracked Project Source candidate drafts, referenced by AG-94C. They are not repo doctrine and should not become default Codex reads. |

## Smallest Durable Doc Spine Proposal

For ordinary architecture work, the durable spine should be:

1. `AGENTS.md`
2. `README.md`
3. `docs/codex/CODEX_GUIDANCE_MAP.md`
4. `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md`
5. `docs/codex/PHASE_BRIEF_TEMPLATE.md`
6. `docs/architecture/SCRYRAVEN_CURRENT_STATE.md`
7. `docs/architecture/AG_CURRENT_PATH_QUARANTINE_01.md`
8. `docs/architecture/RUN_CONTRACT_SEMANTIC_LOOP.md`
9. `docs/architecture/DPRIME_ARCHITECTURE.md`
10. `docs/architecture/ANALYST_WORKBENCH_FULL_SLICE.md`, after cleanup promotes it to a true runtime contract or replaces it with one
11. `docs/architecture/MVP_SUPPORTED_QUERY_CLASS_BOUNDARY.md`, for supported-query/product-path phases
12. `docs/operator/GENERIC_PROVIDER_PROXY_BROKER_OPERATOR_FLOW.md` and `docs/operator/BROKER_REACTIVATION_RUNBOOK.md`, only when live/provider-proxy work is explicitly licensed

This spine keeps Codex from reading every phase note while preserving the
architecture guardrails that prevent patch ping-pong.

## Proposed Default Read Order

| Order | Doc | Why Codex should read it | Constrains | Must not authorize |
| ---: | --- | --- | --- | --- |
| 1 | `docs/codex/CODEX_GUIDANCE_MAP.md` | Chooses the smallest relevant guidance surface. | Routing, current posture, stale-doc conflict handling. | Reading all docs by default or assuming Project Sources are repo files. |
| 2 | `docs/codex/ARCHITECTURE_GROOVE_PLAYBOOK.md` | Defines Path B, Build / Proof / Repair, product-path claims, reuse-first, and final bundle. | Scope, implementation discipline, validation, publication. | Product claims from fixture-only, docs-only, or shadow paths. |
| 3 | `docs/codex/PHASE_BRIEF_TEMPLATE.md` | Provides required phase fields and stop conditions. | Phase shape, validation plan, non-product leash. | Treating a template as a license to open closed surfaces. |
| 4 | Smallest current architecture contract relevant to the phase | Prevents broad context loading. Examples: D-prime, Workbench, live validation, FAP/Author, source hierarchy. | The actual target surface and current consumer seam. | Unrelated historical phase behavior. |
| 5 | Historical phase notes, only if needed | Supplies provenance when the current contract points to it. | Root-cause or migration history. | Current doctrine, product correctness, or default behavior. |

## Stale, Duplicate, Or Misleading Docs

Top cleanup targets:

- `docs/architecture/ANALYST_WORKBENCH_FULL_SLICE.md` is current but incomplete
  as a runtime contract. It should either become the canonical Workbench
  contract or be split into a current contract plus historical phase note.
- `docs/architecture/source_hierarchy_answer_contract_invariants.md` still says
  Controller and AnswerContract own source-obligation fulfillment. That should
  be updated to current RunKernel/RunAuthority vocabulary or marked historical.
- Older `AG74*` through `AG79*` docs repeatedly use Controller-owned and
  protected-surface vocabulary. They should be retained as historical records
  and routed away from ordinary Codex context.
- Several root-level architecture phase records already say "historical phase
  note, demoted by AG-95U" but still sit beside current contracts:
  `AG76C_FE_FINAL_EVIDENCE_BUNDLE_EXTRACTION.md`,
  `AG89D_FINAL_ANSWER_PACKET_AUTHORITY_COLLAPSE.md`,
  `AG90B_FINAL_ANSWER_AUTHOR_CITATION_RUNTIME_SEAM_EXTRACTION.md`,
  `AG90G_POST_ANALYST_HANDOFF_PACKAGING_SEAM.md`,
  `AG90H_POST_AUTHOR_TRACE_OUTCOME_PROJECTION_BURNDOWN.md`, and
  `AG91K_FINAL_ANSWER_PACKET_AUTHOR_EXECUTOR_UNDER_RUNKERNEL.md`.
- `docs/RETRIEVAL_AND_FAILURE_UX_ROADMAP.md` and
  `docs/ROADMAP_IMPLEMENTATION_NOTES.md` are explicitly historical/superseded
  and should stay out of default reads.
- The AG-96 follow-up and SearchWorkPlan docs preserve valuable history but are
  too detailed for default context and overlap current D-prime/follow-up/FAP
  docs.
- `outputs/local_only/ag94c_project_source_candidates/*.md` should not be
  default-read repo doctrine. A later cleanup should decide whether to keep
  them tracked, move them to a clearly archived docs path, or leave them as
  explicitly non-default local candidate material.

## Analyst Workbench Contract Check

Currently documented clearly in `ANALYST_WORKBENCH_FULL_SLICE.md`:

- Workbench is proposal-only.
- Workbench does not admit evidence, satisfy source obligations, create citation
  eligibility, finalize source authority, claim product correctness, or create
  answer prose.
- Workbench may classify candidate roles, propose findings/gap search, prepare
  a D-prime dossier, and prepare a Workbench reduction projection.
- The projection is not RunKernel-reduced yet unless RunKernel actually reduces
  it.

Missing or unclear in repo docs, mostly encoded in
`tests/test_current_source_record_analyst_workbench_01.py` and
`core/analyst_workbench_runtime.py` instead:

- Workbench must not dispatch search directly.
- `strict_support_missing` and `unreadable_high_value_candidate` are explicit
  follow-up triggers when licensed.
- Without follow-up license, those triggers remain blockers with zero follow-up
  provider/fetch calls.
- With follow-up license, they enter existing planned plus RunKernel-authorized
  ordinary follow-up.
- Follow-up execution alone is not product PASS.
- Product PASS requires the existing downstream answer path.
- Workbench expected candidate, D-prime intake candidate, selected source, and
  source display must match before answer authority opens.
- Generic Analyst context vocabulary such as waiver, discount, reduced, online,
  and exception is allowed and should not be removed only to satisfy
  domain-specific static guards.

Result: the Workbench runtime contract is not fully documented in repo docs.
This is the highest-value missing contract for the next cleanup PR.

## Workflow Clarity Check

The Workbench / D-prime / follow-up / AnswerContract / FAP / Author workflow is
partly documented, but not consolidated enough to reliably prevent patch
ping-pong:

- `DPRIME_ARCHITECTURE.md` clearly documents D-prime as evidence-relative
  support judge, not Analyst/Scrutineer/Sufficiency, and documents downstream
  source-obligation, citation-source handoff, FAP, Author, and citation/source
  display consumption.
- `RUN_CONTRACT_SEMANTIC_LOOP.md` clearly separates RunKernel authorization,
  Analyst proposal, Scrutineer review, SufficiencyReadiness, hardened FAP, and
  AuthorProseFinalization.
- `AG_CURRENT_PATH_QUARANTINE_01.md` clearly distinguishes current internal
  authority path from current product-consumed path and historical/proof-only
  debt.
- `ANALYST_WORKBENCH_FULL_SLICE.md` does not yet carry the full Workbench gap
  reentry and identity-match contract.
- `source_hierarchy_answer_contract_invariants.md` still carries old Controller
  ownership language, which can confuse current RunKernel/D-prime work.

## Questions Answered

1. Smallest durable doc spine: the 12-item spine above.
2. Canonical entrypoints: `AGENTS.md`, `README.md`, guidance map, playbook,
   phase template, current-state redirect, quarantine registry, semantic loop,
   D-prime architecture, and cleaned-up Workbench contract.
3. Historical phase notes: most AG74-AG96 architecture records, validation
   notes, old roadmaps, phase handoffs, and Controller-era current-state body.
4. Stale/misleading docs: Controller-era source hierarchy wording, old
   Controller-owned AG74-AG79 docs, old Prove Mode phase docs, historical
   AG-90/AG-91/FAP/Author docs left in architecture root.
5. Duplicative docs: AG-96 follow-up/SearchWorkPlan series overlaps current
   D-prime/follow-up/FAP/Author docs; old current-state and roadmap material
   overlaps the current guidance map and quarantine registry.
6. Old dogfood-only rules: fixture, validation, and AG-96 dogfood notes should
   not govern current product path unless a phase explicitly reopens them.
7. Analyst Workbench runtime contract: incomplete in docs; see missing contract
   list above.
8. Current Workbench/D-prime/follow-up/AnswerContract/FAP/Author workflow:
   mostly documented across multiple docs, not yet compactly consolidated.
9. Required distinctions: D-prime, RunKernel, Scrutineer, Sufficiency/FAP/Author,
   source display/citation eligibility, and live licensing are documented;
   Workbench-specific follow-up and identity-match distinctions are missing.
10. Later cleanup PRs: start with Workbench contract consolidation, then stale
    Controller vocabulary, then historical/archive markings.

## Proposed Cleanup Phases

Phase 1: Workbench runtime contract consolidation.

- Edit `docs/architecture/ANALYST_WORKBENCH_FULL_SLICE.md`.
- Edit `docs/codex/CODEX_GUIDANCE_MAP.md` to route Workbench-adjacent phases to
  it.
- Optionally edit `docs/architecture/DPRIME_ARCHITECTURE.md` only to link the
  Workbench contract and state the handoff identity boundary.
- Expected scope: docs only, no runtime/tests unless an existing docs-static
  guard needs expected-text updates.

Phase 2: Stale Controller vocabulary repair.

- Edit `docs/architecture/source_hierarchy_answer_contract_invariants.md` to
  current RunKernel/RunAuthority ownership vocabulary or mark it historical.
- Add historical banners to selected AG74-AG79 docs if they continue to present
  Controller-era doctrine as current.
- Expected scope: docs only plus any docs/static tests that enforce wording.

Phase 3: Historical archive/routing pass.

- Mark already-demoted AG90/AG91/FAP/Author phase records as historical in a
  consistent banner or move/archive them if a later phase explicitly licenses
  moves.
- Clarify that AG-96 follow-up/SearchWorkPlan docs are historical/supporting
  unless a phase explicitly reopens that stack.
- Decide treatment for tracked `outputs/local_only/ag94c_project_source_candidates/*`.

Phase 4: Default-read and spine hardening.

- Update `docs/codex/CODEX_GUIDANCE_MAP.md` with the final minimal spine after
  Workbench consolidation.
- Add or update a docs-static guard only if the cleanup PR changes required
  routing or status text.

## Recommended Next PR

Recommended next PR: Workbench runtime contract consolidation.

Exact files to edit:

- `docs/architecture/ANALYST_WORKBENCH_FULL_SLICE.md`
- `docs/codex/CODEX_GUIDANCE_MAP.md`
- `docs/architecture/DPRIME_ARCHITECTURE.md`, only for a cross-link if needed

Expected scope:

- Convert the Workbench doc from a phase note into the canonical runtime
  contract, or add a clear canonical-contract section at the top.
- Add the missing `strict_support_missing`,
  `unreadable_high_value_candidate`, follow-up license, zero-call blocker,
  RunKernel ordinary follow-up, product PASS, identity-match, and generic
  vocabulary rules.
- Do not change runtime code.
- Do not delete or move docs in that PR unless separately approved.

## Validation Notes For This Inventory

Existing docs/static guards found:

- `tests/test_ag_phase_mode_operating_system_01.py` guards Build / Proof /
  Repair, current next gate, and retired proof-layer wording across primary
  docs.
- `tests/test_capability_inventory_reuse_guard_01.py` guards the reuse-first
  gate and D-prime downstream reuse lesson.
- `tests/test_ag_current_path_quarantine_01.py` guards the quarantine registry,
  current-vs-product-consumed vocabulary, harness labels, non-proofs, and
  AuthorProse closed surfaces.
- Many seam tests read `docs/architecture/SCRYRAVEN_CURRENT_STATE.md` and
  `docs/codex/CODEX_GUIDANCE_MAP.md` to ensure current posture remains visible.
- D-prime tests read `docs/architecture/DPRIME_ARCHITECTURE.md` to ensure
  request gate, answer path, and product-correctness nonclaims are documented.

No new tests are proposed in this phase. Required checks for this report are
`git diff --check` and `git diff --cached --check`.
