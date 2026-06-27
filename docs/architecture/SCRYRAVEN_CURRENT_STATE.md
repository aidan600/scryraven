# ScryRaven Current State

Status: current-state redirect stub refreshed for
`AG-SCOUT-DISAMBIGUATION-RUNTIME-01`.

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
- Recent main includes PR #312 guarded blocked-FAP Author input derivation,
  PR #313 safe blocked-FAP failure observability summaries, PR #314
  component-level blocked-FAP summary telemetry for blocked semantic
  multipart/source-bound numeric cases, PR #315 offline ComponentPlan /
  component executor contract preservation into passive SearchWork/query-work
  and scorekeeping surfaces, PR #317 RunKernel-owned passive
  AnswerContractAuthorityMap, and PR #318 ComponentSearchPlan naming and
  subordination cleanup. PR #319 / AG-OFFLINE-SEARCH-EXECUTOR-BRIDGE-01
  completed the offline RunKernel-owned SearchExecutor bridge.
- The completed Offline SearchExecutor bridge is offline and inert, does not
  perform live provider/search/fetch/read/retrieval work, does not admit
  EvidenceLedger custody or satisfy source obligations, keeps candidate
  observations non-evidence, and is not user-facing runtime search.
- PR #320 / AG-COMPONENT-SCOPED-SOURCE-CUSTODY-01 adds EvidenceLedger
  component-scoped source custody from offline bridge output. Candidate links
  remain non-evidence until fetched/read/admitted by a later phase, and source
  obligations are unsatisfied/pending rather than satisfied by candidate
  presence.
- AG-COMPONENT-EVIDENCE-CITATION-BINDING-01 extends the existing
  AnswerContractAuthorityMap per-component binding status to consume
  EvidenceLedger component-scoped custody. Offline candidate links and custody
  gaps appear as component-specific blockers, but custody/candidate presence
  does not bind evidence, citations, source obligations, answer values,
  readiness, partial answer authority, or Author handoff.
- PR #322 / AG-SUFFICIENCY-FAP-COMPONENT-READINESS-01 completed existing
  SufficiencyJudgment and FinalAnswerPacket consumption of passive
  AnswerContractAuthorityMap binding status and EvidenceLedger custody inputs
  into component-aware blocked readiness.
- PR #323 / AG-OFFLINE-XAXIS-E2E-01 adds the offline X-axis end-to-end proof
  through blocked FAP / Author handoff. It does not enable partial answers and
  does not enable live validation.
- The current integrated doctrine is the run-contract semantic loop:
  SemanticProducer / SearchPlanner proposes semantic understanding and component
  requirements; RunKernel / RunAuthority governs action authorization, accepted
  contract state, and reducer-gated mutation; Scout, Planner, and SearchExecutor
  are workers; EvidenceLedger owns custody; SemanticObservation and
  ComponentCoverage own evidence-relative meaning and support; SufficiencyJudgment
  decides readiness; FinalAnswerPacket packages Author-safe handoff; Author
  writes prose only.
- AG-RUN-CONTRACT-MUTATION-LOOP-01 applies admitted amendments through
  RunKernel into `current_answer_contract`, while `initial_answer_contract`
  remains immutable genesis state.
- AG-SEARCH-PLANNER-RUNTIME-01 completes the RunKernel-authorized
  SearchPlanner proposal seam: an explicitly injected adapter can produce a
  passive QMR-compatible proposal plus subordinate component-search
  requirements, while live model/search/fetch/read/retrieval behavior remains
  closed and amendments remain deferred.
- AG-SEARCH-PLANNER-MODEL-01 adds an explicit injected fail-closed model adapter
  behind the existing SearchPlanner runtime seam. The adapter can call an
  injected model callable only when explicitly enabled/licensed, validates
  strict JSON planner output, and returns sanitized proposal data consumed
  through existing RunKernel planner and contract reducers. Tests use fake
  injected model callables. No live model calls or live validation were run.
- Previous baseline: PR #327 / AG-SEARCH-PLANNER-MODEL-01.
- This PR: AG-SCOUT-DISAMBIGUATION-RUNTIME-01 adds a RunKernel-authorized,
  report-only, Serper-shaped Scout DisambiguationReport runtime.
- Scout is future-Serper-ready, but this PR uses fake injected adapters only.
- No live Serper/search/provider/model/fetch/read/retrieval calls were run.
- Scout hints are not evidence, not citations, and not source-obligation
  satisfaction.
- Scout hints are not evidence, not citations, and not source-obligation satisfaction.
- Scout does not mutate contracts.
- Scout does not revise planner output.
- SearchExecutor, fetch/read/retrieval, Author, citations, partial answers, and
  live validation remain closed.
- The post-merge next gate is AG-SEARCH-PLANNER-REVISION-01.
- Passive/shadow surfaces are not product readiness.
- No live validation is part of the current posture.
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
