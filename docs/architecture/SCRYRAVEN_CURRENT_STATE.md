# ScryRaven Current State

Status: current-state redirect stub refreshed for
`AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01` after PR #342 /
`AG-COMPONENT-COVERAGE-RELIABILITY-PROOF-01` and the docs checkpoint.

This file used to contain a long Controller-era rollup under a current-looking
filename. That body is preserved as historical record at
`docs/architecture/historical/SCRYRAVEN_CURRENT_STATE_CONTROLLER_ERA_HISTORICAL.md`.

For current authority doctrine and Codex routing, read:

- `docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md`
- `docs/architecture/AG_DOC_SEMANTIC_COVERAGE_CHECKPOINT_01.md`
- `docs/architecture/RUN_CONTRACT_SEMANTIC_LOOP.md`
- `docs/architecture/AG94C_AUTHORITY_DOCTRINE_DETRITUS_AUDIT.md`
- `docs/architecture/AG94G_ORCHESTRATOR_AUTHORITY_STRANGLER_MAP.md`

Current summary:

- ScryRaven is the public project name.
- RunAuthority / RunKernel is the current authority direction.
- `core/pipeline_orchestrator.py` is a coordination shell with remaining
  authority debt.
- In ordinary product behavior phases the orchestrator may be closed for scope
  safety.
- In orchestrator-strangulation phases the orchestrator is a licensed target
  surface.
- `pipeline_orchestrator.py` line delta `0` is a scope-control fact, not
  architecture success.
- The current integrated doctrine is the run-contract semantic loop:
  SearchPlanner proposes semantic understanding and component requirements;
  RunKernel / RunAuthority governs action authorization, accepted contract
  state, and reducer-gated mutation; Scout, SearchPlannerRevision, and
  SearchExecutorHandoff are workers; EvidenceLedger owns custody only after
  admissible sanitized content exists; SemanticObservation admission is the
  controlled promotion from proposal-stage meaning to admitted meaning;
  ComponentCoverage consumes admitted meaning and custody bindings; Sufficiency
  decides readiness; FinalAnswerPacket packages Author-safe handoff; Author
  writes prose only.
- The coherent front half is:
  `SearchPlanner -> initial_answer_contract -> Scout -> SearchPlannerRevision ->
  amendment admission/application -> current_answer_contract ->
  SearchExecutorHandoff`.
- `SearchExecutorHandoff` is search intent only. It creates query-intent
  records, search-task records, and a search work packet; it does not call
  providers, execute live search, fetch/read, admit EvidenceLedger custody,
  create citations, satisfy source obligations, decide Sufficiency, create FAP
  state, create Author input, or make partial answers ready.
- SearchExecutorHandoff exact posture: PR #330 / AG-SEARCH-EXECUTOR-HANDOFF-01; handoff consumes current_answer_contract when present; Scout/revision material is search direction only; handoff creates search task records and a search work packet; no live search/provider/fetch/read/retrieval calls were run; no EvidenceLedger/citations/source-obligation satisfaction; next implementation gate after AG-SECOND-HALF-SEMANTIC-ARCHITECTURE-01 is AG-LIVE-XAXIS-VALIDATION-01A.
- Historical SearchPlannerRevision exact posture: PR #329 / AG-SEARCH-PLANNER-REVISION-01; planner revision consumes Scout report; planner revision emits passive amendment candidates; Scout hints remain non-evidence, non-citation, and non-source-obligation satisfaction; current_answer_contract changes only through existing admission/application path; SearchExecutor, fetch/read/retrieval remain closed; post-merge next gate was AG-SEARCH-EXECUTOR-HANDOFF-01.
- Historical Scout exact posture: PR #327 / AG-SEARCH-PLANNER-MODEL-01; AG-SCOUT-DISAMBIGUATION-RUNTIME-01; RunKernel-authorized; report-only; Serper-shaped; fake injected adapters only; No live Serper/search/provider/model/fetch/read/retrieval calls were run; Scout hints are not evidence; not citations; not source-obligation satisfaction; Scout does not mutate contracts; Scout does not revise planner output; post-merge next gate is AG-SEARCH-PLANNER-REVISION-01.
- Historical SearchPlannerModel exact posture: PR #327 / AG-SEARCH-PLANNER-MODEL-01; AG-SEARCH-PLANNER-RUNTIME-01; AG-SEARCH-PLANNER-MODEL-01 adds an explicit injected fail-closed model adapter; No live model calls or live validation were run; AG-SCOUT-DISAMBIGUATION-RUNTIME-01; Scout hints are not evidence; post-merge next gate is AG-SEARCH-PLANNER-REVISION-01.
- `AG-LIVE-XAXIS-VALIDATION-01A` PR1 introduced a RunKernel-owned
  search-only validation seam that consumes `current_answer_contract` plus
  `SearchExecutorHandoff` directly and emits sanitized `SearchResultCandidate`
  records only from injected fake-provider results. PR2 adds shared
  broker/direct invocation scaffolding only: request schema, cap policy,
  provider allowlist, candidate normalizer, redaction posture, output-packet
  shape, and inert wrapper scripts. Durable broker contact should use the
  generic provider-proxy contract, not a phase-specific broker job. PR2 does
  not run live validation, call a broker, or call a provider unless separately
  licensed after review.
- `AG-LIVE-XAXIS-VALIDATION-01A-LIVE-RUN-01` adds an inert trusted-local
  harness that prepares the repo-visible request packet and optional broker
  envelope from deterministic current-contract plus SearchExecutorHandoff
  state. When actual provider contact is separately licensed, it should use the
  generic provider-proxy broker contract via
  `scripts/run_provider_proxy_broker_once.py` and separately supplied sanitized
  provider-result JSON, not a phase-specific broker job. The helper produces
  generic sanitized output under `output/`; LIVE-RUN-01 maps that output into a
  task-keyed provider-results JSON written UTF-8 without BOM, then reduces it
  through
  `scripts/ag_live_xaxis_validation_01a_live_run_01_harness.py --reduce-sanitized-results --execution-mode broker_live`.
  That mapping is task-specific and does not belong inside the broker. The
  harness can reduce sanitized provider-result JSON through the existing
  RunKernel path, but it does not call providers, call a broker, load
  credentials, fetch/read, retrieve, admit evidence, create citations, decide
  Sufficiency, create FAP or Author input, make partial-readiness claims, or
  claim product correctness.
- `AG-LIVE-XAXIS-VALIDATION-01A` must not claim fetch/read, EvidenceLedger
  admission, citations, source-obligation satisfaction, Sufficiency, FAP,
  Author, partial-answer readiness, product correctness, or final answer
  quality.
- `broker_invoked` and `live_provider_called` are PR2 execution facts, not
  downstream evidence/readiness authority and not members of
  `closed_surface_flags`. Raw provider payload and raw search response
  retention remain false in every mode.
- `provider_preference_hint` is only a hint. Live provider authority must come
  from an explicit RunKernel-authorized validation action and explicit
  `provider_authorized` request value.
- Existing `core/search_providers.py` provider wrappers, including Serper, may
  be reused only behind a governed live-search-validation adapter.
- `core/offline_search_executor_bridge.py` remains legacy/offline scaffolding
  for the old X-axis proof path. It should be demoted, retired, or ignored for
  the new handoff-consuming live path.
- The current semantic-coverage chain is:
  `SearchResultCandidatePacket -> FetchReadContentPacket /
  SanitizedContentReference -> EvidenceLedger custody ->
  EvidenceRelativeAnalysisPacket / AnalystReport -> FollowupSearchIntentPacket /
  AnalysisGapSearchProposal -> ComponentCoverage reliability proof ->
  SemanticObservation admission bridge -> ComponentCoverage reduction -> next:
  Scrutineer MVP`.
- `SearchResultCandidatePacket` is the durable non-evidence candidate handoff
  before fetch/read. It preserves sanitized live-search candidate lineage, but
  search candidates are not evidence, not citation-eligible, and the packet does
  not satisfy source obligations.
- `FetchReadContentPacket` / `SanitizedContentReference` is the bounded
  readable-content handoff after `SearchResultCandidatePacket` and before
  EvidenceLedger custody; it is not evidence, not citation-eligible, and does
  not satisfy source obligations.
- `AG-EVIDENCE-LEDGER-CANDIDATE-CUSTODY-01` adds the RunKernel-authorized
  `FetchReadContentPacket` / `SanitizedContentReference` -> EvidenceLedger
  candidate/content custody seam. EvidenceLedger now records sanitized packet,
  candidate, reference, status, URL/domain/title, and bounded-content
  count/digest lineage, but this custody is not semantic support, not
  citation-eligible, does not satisfy source obligations, and does not decide
  Sufficiency/FAP/Author readiness or product correctness.
- `AG-ANALYST-EVIDENCE-RELATIVE-REPORT-01` introduces
  `EvidenceRelativeAnalysisPacket` with embedded `analyst_report` as
  proposal-only evidence-relative meaning after EvidenceLedger custody. It
  consumes fetch/read custody IDs and digests plus injected offline Analyst
  proposal records; it is not SemanticObservation admission and does not create
  ComponentCoverage, citation eligibility, source-obligation satisfaction,
  Sufficiency, FinalAnswerPacket, Author input, readiness, partial-answer
  readiness, or product correctness.
- `AG-ANALYSIS-GAP-FOLLOWUP-SEARCH-01` introduces
  `FollowupSearchIntentPacket` / `AnalysisGapSearchProposal` as the current
  proposal-only gap-to-search-intent posture from validated
  `EvidenceRelativeAnalysisPacket` / `analyst_report.analysis_gap_proposals`.
  It is not search authorization, not a query plan, does not create
  SearchExecutorHandoff, does not dispatch search, does not create evidence,
  and RunKernel/SearchPlanner/SearchExecutorHandoff authorization remains
  required before any executable search work exists.
- `AG-COMPONENT-COVERAGE-RELIABILITY-PROOF-01` completed the
  ComponentCoverage reliability proof. The phase-focus
  `component_coverage_reliability_report` showed that ComponentCoverage can
  reduce meaningful support only after admitted `SemanticObservation` exists.
  The packet chain by itself does not admit semantic support.
- `AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01` completes the minimal bridge
  before Scrutineer or Specialist. It is the controlled promotion from Analyst
  support proposal to admitted SemanticObservation, justified because
  ComponentCoverage consumes it immediately:
  `EvidenceRelativeAnalysisPacket` support finding -> RunKernel-authorized
  `SemanticObservation` admission -> ComponentCoverage reduction.
- The bridge is not a new durable proposal packet. ComponentCoverage reduction
  remains separate and must consume the admitted observation and content binding.
- The bridge does not create source-obligation satisfaction, citation
  eligibility, Sufficiency, FinalAnswerPacket, Author input, live search,
  provider calls, broker calls, retrieval, fetch/read execution, model calls, or
  product correctness.
- Blocked/follow-up gap-to-ComponentCoverage blocker lineage remains a
  downstream gap unless solved later without packet sprawl.
- The packet/bridge budget rule is now explicit: no new packet or bridge unless
  it crosses a trust/raw-data boundary, becomes durable reducer input, needs
  stable downstream IDs/digests consumed by more than one stage, records
  canonical or reducer-admitted state, prevents raw/private/provider leakage, or
  removes a named blocker for an existing consumer. A packet or bridge is
  suspect if it only restates lineage, only says closed flags remain false, is
  only consumed by its own tests, creates another proposal layer without
  reduction, or has no immediate consumer in the same or next phase.
- Broker is local/private validation plumbing, not installed-product authority
  and not product follow-up policy.
- Modes change budget and review depth, not semantic authority. Follow-up policy
  should use logical depth, loop budget, query fanout, and RunKernel approval,
  not one-query-per-proposal. Fast has no Scrutineer in MVP. Balanced uses
  Scrutineer on red flags. Deep requires Scrutineer and post-Scrutineer
  response budget, with max 3 follow-up loops by default and max 4 only with
  explicit RunKernel extra recovery authorization.
- Specialist MVP is deferred and should start as source-bound
  calculation/economist-style reasoning only.
- The AG-96 followup stack, offline SearchExecutor bridge, SearchWorkPlan
  shadow, old Analyst/Economist/Scrutineer paths, source-class recovery bridges,
  and broad pipeline orchestrator paths are legacy/passive/closed unless
  explicitly reopened.
- Existing Analyst, Economist, and Scrutineer surfaces are not yet a coherent
  new RunKernel/current_answer_contract second-half semantic architecture.
- Partial-answer readiness is premature until ComponentCoverage, Sufficiency,
  FAP, and Author-safe prerequisites are coherent.
- The roadmap order is:
  `AG-SECOND-HALF-SEMANTIC-ARCHITECTURE-01`,
  `AG-LIVE-XAXIS-VALIDATION-01A`,
  `AG-SEARCH-RESULT-CANDIDATE-PACKET-01`,
  `AG-FETCH-READ-CONTENT-REFERENCE-01`,
  `AG-EVIDENCE-LEDGER-CANDIDATE-CUSTODY-01`,
  `AG-ANALYST-EVIDENCE-RELATIVE-REPORT-01`,
  `AG-ANALYSIS-GAP-FOLLOWUP-SEARCH-01`,
  `AG-COMPONENT-COVERAGE-RELIABILITY-PROOF-01`,
  `AG-DOC-SEMANTIC-COVERAGE-CHECKPOINT-01`,
  `AG-SEMANTIC-OBSERVATION-ADMISSION-BRIDGE-01`,
  next likely gate after this bridge is Scrutineer MVP,
  then source-bound calculation Specialist MVP,
  then Sufficiency / partial-answer readiness,
  then FAP hardening,
  then Author prose-only finalization.
- The historical broad `AG-LIVE-BOUND-01` product-run plan is later planning
  history, not the immediate post-#330 search-only validation plan.
- Passive/shadow surfaces are not product readiness.
- No live provider call, broker invocation, fetch/read, or retrieval was run as
  part of PR1 or PR2.
- AnswerContractAuthorityMap owns answer-component authority mapping.
- ComponentPlan is legacy/compat input terminology; ComponentSearchPlan is the
  preferred subordinate component-search planning name.
- ComponentPlan / ComponentSearchPlan are useful but passive and subordinate;
  they do not decide answerability, source-obligation satisfaction, final
  readiness, citation eligibility, or Author handoff.
- Relevant semantic-lane history remains in
  `AG_SEM_01_PASSIVE_SEMANTIC_CONTRACT_FOUNDATION.md`,
  `AG_SEM_02_SANITIZED_CONTENT_REFERENCE_AND_SEMANTIC_OBSERVATION.md`,
  `AG_SEM_04_CONTRACT_AMENDMENT_RECORD.md`,
  `AG_SEM_05_INITIAL_ANSWER_CONTRACT_ACCEPTANCE.md`,
  `AG_SEM_07_COMPONENT_COVERAGE_REDUCTION.md`,
  `AG_SEM_08_CONTRACT_AMENDMENT_ADMISSION.md`,
  `AG_SEM_09_SUFFICIENCY_SEMANTIC_CONSUMPTION.md`,
  `AG_SEM_11_ORDINARY_SEMANTIC_PRODUCER_VERTICAL_SLICE.md`, and
  `AG_SEM_11B_ORDINARY_SEMANTIC_PRODUCER_HARDENING.md`.
