# AG-SEM-06 Canonical SemanticObservation Admission

Status: Canonical authority bridge. Second canonical semantic authority bridge.

## Proof Class

`offline_product_path_proof`

## Scope

AG-SEM-06 lets a RunKernel/RunAuthority-authorized reducer admit exactly one
validated passive `SemanticObservation` proposal (AG-SEM-02), with its required
sanitized content references, into canonical RunKernel-owned
observation-admission state.

The product-path delta is limited to RunKernel canonical state. Given an
authorized action, an accepted AG-SEM-05 initial answer contract, a valid passive
`SemanticObservation`, and valid sanitized content references, RunKernel creates
canonical semantic-observation admission state, projection, and history.

This phase admits observations only. It does not reduce coverage, amend the
contract, decide Sufficiency, create Author input, change search/provider
behavior, or change final-answer behavior.

## Actual App Delta

- New bounded runtime module `core/semantic_observation_admission_runtime.py`
  builds and validates the canonical admission state and its projection. It
  reuses the AG-SEM-02 `SemanticObservation` / `SanitizedContentReference`
  records and validators so the admission digest and content-ref validation stay
  consistent with the passive foundation. It does not import `core.run_kernel`,
  keeping the import graph acyclic.
- `core/run_kernel.py` gains:
  - action type `ActionType.SEMANTIC_OBSERVATION_ADMIT`
    (`"semantic_observation_admit"`)
  - observation type `ObservationType.SEMANTIC_OBSERVATION_ADMITTED`
    (`"semantic_observation_admitted"`)
  - stage `SEMANTIC_OBSERVATION_ADMISSION_STAGE`
    (`"semantic_observation_admission"`)
  - `RunState` fields `semantic_observation_admission_state`,
    `semantic_observation_admission_projection`, and
    `semantic_observation_admission_history` (mirrored into
    `KernelTraceProjection`)
  - authorization helper
    `RunKernel.authorize_semantic_observation_admission(...)` which requires an
    accepted initial answer contract and binds the observation id/digest, the
    answer component id/revision/digest, and the accepted contract
    digest/version into the authorized action
  - a reducer branch that builds canonical state, projection, and history.

## Runtime Consumer

The RunKernel reducer/state/projection is the immediate canonical consumer; the
intended downstream runtime consumer is a future canonical coverage reducer. The
admission moves a passive observation (AG-SEM-02) into RunKernel-owned canonical
admission state without granting it coverage or satisfaction authority.

## Required Canonical State

The canonical admission state records the schema/version identifier, owner,
`canonical_state` true, `trace_only`/`storage_only` false, `run_id`,
`request_id`, the authorized action id, the observation id and recomputed
observation digest, the accepted contract version and digest, the parent
`QuestionMeaningRecord` id and digest, the answer component id, the accepted
component revision and digest, the cited evidence refs, the cited content-ref
ids and recomputed content digests, the observation kind, support status, support
kind and directness, a bounded/sanitized claim-or-value projection, the
normalization/scope/assumption fit when present, the candidate caveats,
follow-up gaps, and amendment notes as candidate-only, a lineage block
(`created_by`, `created_from`, `reducer_action_id`, parent observation digest,
accepted contract digest), a deterministic `admission_digest`, and a set of
closed-surface false flags (`coverage_created`, `component_satisfied`,
`amendment_created`, `sufficiency_decided`, `final_answer_packet_created`,
`author_input_created`, `search_judgment_decided`, `query_plan_activated`,
`search_work_plan_activated`, `followup_authorized`, `citation_behavior_changed`,
`provider_search_behavior_changed`, `runtime_behavior_changed`, and
`live_validation_not_run` true). The projection carries no raw or private data.

## Required Semantics

The reducer admits the observation only. Candidate caveats, follow-up gaps, and
amendment notes carried by an admitted observation remain candidate-only: they
never create coverage, amendments, follow-up, or Author input. Material ambiguity
and contract obligations from AG-SEM-05 are unchanged.

## Validation And Rejection

Admission requires an accepted AG-SEM-05 initial answer contract and an issued
authorized action with exact run/action/stage/observation binding. It recomputes
the `SemanticObservation` digest from the actual payload content and rejects
stale or tampered observation payloads; it recomputes each
`SanitizedContentReference` content digest from the bounded content / structured
value and rejects stale or tampered content references. It validates the
observation against its provided sanitized content refs using the AG-SEM-02
validators (support-bearing observations require answer-bearing content refs;
missing or incompatible content refs are rejected; refs must remain sanitized and
bounded).

It validates exact accepted-contract binding (observation contract version and
digest match the accepted contract; observation parent `QuestionMeaningRecord`
id and digest match the accepted parent QMR), exact component binding
(`answer_component_id` exists in the accepted component refs; component revision
matches; component contract digest matches the accepted component digest), and
content-ref binding (each cited content ref exists, matches the observation and
accepted component id/revision/digest, and matches the accepted parent QMR
id/digest). It validates EvidenceLedger custody refs against the current RunState
evidence-ledger projection: every cited evidence id (observation evidence refs
and content-ref evidence ids) must correspond to an existing ledger
candidate/custody ref in the ledger's normalized custody identity space, and
foreign or missing refs are rejected. It rejects duplicate observation ids and
digests and stale/replayed reductions, and stores only sanitized, bounded,
projection-safe fields.

## EvidenceLedger Custody Support

The current AG-91J `EvidenceLedger` projection exposes candidate-level custody
through `candidate_records`, `custody_records`, `requirement_links`, and the
`linked_candidate_ids` of `source_requirements`. This is sufficient to reject
foreign or missing evidence refs without a broad EvidenceLedger refactor. The
ledger casefolds candidate ids and maps hyphens/spaces to underscores; the
admission bridge normalizes cited refs into that same identity space before
comparison.

## Closed Surfaces

This phase does not add a `ComponentCoverageRecord` reducer, a
`ContractAmendmentRecord` acceptance/reduction, `SufficiencyJudgment` behavior,
`SearchJudgment` / `QueryPlan` / `SearchWorkPlan` / follow-up behavior,
`FinalAnswerPacket` behavior, Author payload/prompt/prose/execution/finalization
behavior, provider/search/retrieval/fetch/read behavior, or citation behavior. It
does not turn `SemanticObservation` into coverage or satisfaction authority and
does not introduce a generic semantic framework.

No live validation is allowed. `core/pipeline_orchestrator.py` is unchanged
(expected delta 0). No package/CLI/env rename is performed.

## Relationship To AG-SEM-01..05

AG-SEM-06 consumes the AG-SEM-02 passive `SemanticObservation` and
`SanitizedContentReference` records by id and digest and binds them to the
AG-SEM-05 accepted initial answer contract by contract version/digest, parent QMR
id/digest, and component id/revision/digest. It does not reduce AG-SEM-03
`ComponentCoverageRecord` or accept AG-SEM-04 `ContractAmendmentRecord`; those
remain closed and are the subject of later canonical bridges.

## Validation

New tests are classified as `phase_focus` and are not added to `fast_pr` in this
phase. Phase validation includes the AG-SEM-06 focused test, the immediate
AG-SEM-01/02/03/04/05 producer-contract tests, the AG-91H RunKernel spine test,
touched-file lint/format checks, pre-commit for touched files, and
`git diff --check`.
