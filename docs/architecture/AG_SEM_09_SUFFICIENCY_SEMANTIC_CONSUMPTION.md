# AG-SEM-09 Canonical Sufficiency Semantic Consumption

Status: Canonical authority bridge. Fifth canonical semantic authority bridge.

## Proof Class

`offline_product_path_proof`

## Scope

AG-SEM-09 lets a RunKernel/RunAuthority-authorized reducer record exactly one
canonical Sufficiency semantic-consumption binding over the accepted AG-SEM-05
initial answer contract, AG-SEM-06 admitted `SemanticObservation` history,
AG-SEM-07 reduced component coverage history, and optional AG-SEM-08 admitted
`ContractAmendmentRecord` candidates.

The product-path delta is limited to RunKernel canonical state. Given an
authorized action, an accepted initial answer contract, at least one admitted
observation, at least one reduced coverage record, valid EvidenceLedger custody
projection, and optional amendment-admission history, RunKernel creates canonical
Sufficiency semantic-consumption state, projection, and history.

This phase records semantic consumption only. It does not mutate the accepted
initial answer contract, apply amendment candidates, mark coverage stale, apply
coverage invalidation, decide SufficiencyJudgment, decide SearchJudgment,
activate QueryPlan/SearchWorkPlan, authorize follow-up, create Author input,
change search/provider behavior, or change final-answer or citation behavior.

## Actual App Delta

- New bounded runtime module `core/sufficiency_semantic_consumption_runtime.py`
  builds and validates the canonical semantic-consumption state and its
  projection. It does not import `core.run_kernel` or follow-up/Sufficiency
  runtime modules, keeping the import graph acyclic.
- `core/run_kernel.py` gains:
  - action type `ActionType.SUFFICIENCY_SEMANTIC_CONSUME`
    (`"sufficiency_semantic_consume"`)
  - observation type `ObservationType.SUFFICIENCY_SEMANTIC_CONSUMED`
    (`"sufficiency_semantic_consumed"`)
  - stage `SUFFICIENCY_SEMANTIC_CONSUMPTION_STAGE`
    (`"sufficiency_semantic_consumption"`)
  - `RunState` fields `sufficiency_semantic_consumption_state`,
    `sufficiency_semantic_consumption_projection`, and
    `sufficiency_semantic_consumption_history` (mirrored into
    `KernelTraceProjection`)
  - authorization helper `RunKernel.authorize_sufficiency_semantic_consumption(...)`
    which requires an accepted initial answer contract, at least one admitted
    observation, and at least one reduced coverage record, and binds
    `semantic_consumption_id`, `accepted_contract_digest`, and
    `accepted_contract_version` into the authorized action
  - a reducer branch that builds canonical state, projection, and history without
    mutating upstream semantic authority.

## Runtime Consumer

The RunKernel reducer/state/projection is the immediate canonical consumer; the
intended downstream runtime consumer is a future Sufficiency judgment input
assembly reducer. The consumption binding moves canonical semantic stack refs into
RunKernel-owned Sufficiency semantic-consumption state without granting
SufficiencyJudgment, Author, or final-answer authority.

## Required Canonical State

The canonical consumption state records the schema/version identifier, owner,
`canonical_state` true, `trace_only`/`storage_only` false, `run_id`,
`request_id`, the authorized action id, the `semantic_consumption_id`, accepted
contract version/digest/ref bindings, parent `QuestionMeaningRecord` bindings,
consumed observation refs, consumed coverage refs (preserving `stale` as-is with
`coverage_marked_stale` false), optional consumed amendment-admission refs with
`amendment_applied` false and `represented_only` true, EvidenceLedger binding,
component coverage summary, consumption posture, recommended next step, a lineage
block, a deterministic `semantic_consumption_digest`, and closed-surface false
flags (`initial_answer_contract_mutated`, `amendment_applied`,
`coverage_marked_stale`, `coverage_invalidation_applied`, `contract_mutation_applied`,
`sufficiency_decided`, `final_answer_packet_created`, `author_input_created`,
`search_judgment_decided`, `query_plan_activated`, `search_work_plan_activated`,
`followup_authorized`, `citation_behavior_changed`,
`provider_search_behavior_changed`, `runtime_behavior_changed`, and
`live_validation_not_run` true). The projection carries no raw or private data.

## Required Semantics

The reducer records semantic consumption only. Stale coverage may be present in
consumed refs without marking canonical coverage stale or applying invalidation.
Admitted amendment candidates may be represented as optional consumption refs
without applying amendments or mutating the accepted initial answer contract.

## Validation And Rejection

Consumption requires an accepted AG-SEM-05 initial answer contract, at least one
AG-SEM-06 admitted `SemanticObservation`, at least one AG-SEM-07 reduced
`ComponentCoverageRecord`, and an issued authorized action with exact
run/action/stage/observation binding. It rejects authority/closed-surface taint
on the raw payload before reconstruction.

It validates exact contract binding, admitted observation refs cited by reduced
coverage history, coverage refs against accepted component refs, optional
amendment-admission refs as represented-only metadata, and EvidenceLedger binding
via a local projection digest helper. It rejects duplicate
`semantic_consumption_id` or digest replay and stores only sanitized, bounded,
projection-safe fields.

## Closed Surfaces

No initial answer contract mutation, no amendment application, no coverage stale
marking, no coverage invalidation application, no SufficiencyJudgment behavior,
no SearchJudgment / QueryPlan / SearchWorkPlan / follow-up behavior, no
FinalAnswerPacket or Author behavior, no provider/search/retrieval/fetch/read
behavior, no citation behavior, no live validation, and no
`core/pipeline_orchestrator.py` changes (expected delta 0).

## Relationship To Prior AG-SEM Phases

- Consumes AG-SEM-05 accepted initial answer contract
- Consumes AG-SEM-06 admitted `SemanticObservation` history
- Consumes AG-SEM-07 reduced component coverage history
- Optionally consumes AG-SEM-08 admitted `ContractAmendmentRecord` candidates as
  represented-only refs
- Does not decide SufficiencyJudgment or assemble final Sufficiency input yet

## Validation

New tests are classified as `phase_focus` and are not added to `fast_pr` in this
phase.

- `tests/test_ag_sem_09_sufficiency_semantic_consumption.py`
- `tests/test_ag_sem_01_passive_semantic_contract_foundation.py` through
  `tests/test_ag_sem_08_contract_amendment_admission.py`
- `tests/test_run_kernel_ag91h.py`
- touched-file `ruff check`, `pre-commit`, and `git diff --check`
