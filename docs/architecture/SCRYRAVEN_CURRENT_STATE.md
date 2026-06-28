# ScryRaven Current State

Status: current-state redirect stub refreshed for
`AG-LIVE-XAXIS-VALIDATION-01A` PR2 after PR #330 /
`AG-SEARCH-EXECUTOR-HANDOFF-01`.

This file used to contain a long Controller-era rollup under a current-looking
filename. That body is preserved as historical record at
`docs/architecture/historical/SCRYRAVEN_CURRENT_STATE_CONTROLLER_ERA_HISTORICAL.md`.

For current authority doctrine and Codex routing, read:

- `docs/codex/RUNAUTHORITY_IMPLEMENTATION_GUIDE.md`
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
  admissible sanitized content exists; SemanticObservation and ComponentCoverage
  own evidence-relative meaning and support; SufficiencyJudgment decides
  readiness; FinalAnswerPacket packages Author-safe handoff; Author writes
  prose only.
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
- The second-half semantic packet/report chain is:
  `SearchResultCandidatePacket -> FetchReadContentPacket /
  SanitizedContentReference -> EvidenceLedger custody ->
  EvidenceRelativeAnalysisPacket / AnalystReport -> SpecialistAnalysisPacket
  when needed -> ScrutineerReview -> ComponentCoverageRecord proposals ->
  ContractAmendmentRecord proposals -> SufficiencyJudgment ->
  FinalAnswerPacket -> Author prose only`.
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
- `AnalysisGapSearchProposal` is the future proposal shape for analysis,
  specialist, or Scrutineer-discovered search gaps. It must route back through
  RunKernel authority and must not dispatch on its own.
- Existing Analyst, Economist, and Scrutineer surfaces are not yet a coherent
  new RunKernel/current_answer_contract second-half semantic architecture.
- Partial-answer readiness is premature until an evidence-relative
  Analyst/Specialist/Scrutineer/Sufficiency/FAP packet chain exists.
- The roadmap order is:
  `AG-SECOND-HALF-SEMANTIC-ARCHITECTURE-01`,
  `AG-LIVE-XAXIS-VALIDATION-01A`,
  `AG-SEARCH-RESULT-CANDIDATE-PACKET-01`,
  `AG-FETCH-READ-CONTENT-REFERENCE-01`,
  `AG-EVIDENCE-LEDGER-CANDIDATE-CUSTODY-01`,
  `AG-ANALYST-EVIDENCE-RELATIVE-REPORT-01`,
  then later `AG-PARTIAL-ANSWER-READINESS-01`.
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
