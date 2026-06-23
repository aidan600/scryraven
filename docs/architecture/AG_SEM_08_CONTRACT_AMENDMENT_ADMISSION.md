# AG-SEM-08 Canonical ContractAmendmentRecord Admission

Status: Canonical authority bridge. Fourth canonical semantic authority bridge.

## Proof Class

`offline_product_path_proof`

## Scope

AG-SEM-08 lets a RunKernel/RunAuthority-authorized reducer admit exactly one
validated passive `ContractAmendmentRecord` proposal (AG-SEM-04) into canonical
RunKernel-owned contract-amendment admission state.

The product-path delta is limited to RunKernel canonical state. Given an authorized
action, an accepted AG-SEM-05 initial answer contract, valid trigger-ref bindings
against admitted observations, reduced coverage, cited content refs, and
EvidenceLedger custody, and a valid passive `ContractAmendmentRecord`, RunKernel
creates canonical amendment admission state, projection, and history.

This phase admits amendment candidates only. It does not mutate the accepted
initial answer contract, mark coverage stale, apply coverage invalidation, consume
coverage in Sufficiency, decide SearchJudgment, activate QueryPlan/SearchWorkPlan,
authorize follow-up, create Author input, change search/provider behavior, or
change final-answer or citation behavior.

## Actual App Delta

- New bounded runtime module `core/contract_amendment_admission_runtime.py`
  builds and validates the canonical admission state and its projection. It
  reuses the AG-SEM-04 `ContractAmendmentRecord` record and validators so the
  amendment digest and passive invariants stay consistent with the passive
  foundation. It does not import `core.run_kernel` or follow-up/Sufficiency
  runtime modules, keeping the import graph acyclic.
- `core/run_kernel.py` gains:
  - action type `ActionType.CONTRACT_AMENDMENT_ADMIT`
    (`"contract_amendment_admit"`)
  - observation type `ObservationType.CONTRACT_AMENDMENT_ADMITTED`
    (`"contract_amendment_admitted"`)
  - stage `CONTRACT_AMENDMENT_ADMISSION_STAGE`
    (`"contract_amendment_admission"`)
  - `RunState` fields `contract_amendment_admission_state`,
    `contract_amendment_admission_projection`, and
    `contract_amendment_admission_history` (mirrored into `KernelTraceProjection`)
  - authorization helper `RunKernel.authorize_contract_amendment_admission(...)`
    which requires an accepted initial answer contract and binds amendment record
    id/digest, parent contract version/digest, and accepted contract
    digest/version into the authorized action
  - a reducer branch that builds canonical state, projection, and history.

## Runtime Consumer

The RunKernel reducer/state/projection is the immediate canonical consumer; the
intended downstream runtime consumer is a future contract-amendment acceptance or
application reducer. The admission moves a passive amendment record (AG-SEM-04)
into RunKernel-owned canonical admission state without granting contract mutation,
coverage invalidation, Sufficiency, Author, or final-answer authority.

## Required Canonical State

The canonical admission state records the schema/version identifier, owner,
`canonical_state` true, `trace_only`/`storage_only` false, `run_id`,
`request_id`, the authorized action id, the amendment record id and recomputed
amendment record digest, parent and accepted contract version/digest bindings,
optional `accepted_contract_ref`, disposition and posture fields, trigger refs,
affected component refs, operations, candidate invalidated coverage refs
(`represented_only` true, `coverage_invalidation_applied` false), stale-coverage
candidate posture, required caveats, prohibited upgrades, rejection/blocking
reasons, a lineage block (`created_by`, `created_from`, `reducer_action_id`,
parent amendment record digest, accepted contract digest), a deterministic
`admission_digest`, and closed-surface false flags (`contract_mutation_applied`,
`coverage_invalidation_applied`, `coverage_marked_stale`,
`initial_answer_contract_mutated`, `amendment_applied`, `sufficiency_decided`,
`final_answer_packet_created`, `author_input_created`, `search_judgment_decided`,
`query_plan_activated`, `search_work_plan_activated`, `followup_authorized`,
`citation_behavior_changed`, `provider_search_behavior_changed`,
`runtime_behavior_changed`, and `live_validation_not_run` true). The projection
carries no raw or private data.

## Required Semantics

The reducer admits amendment candidates only. Rejected or blocked dispositions may
be admitted when `ContractAmendmentRecord.validate()` passes. Candidate stale
coverage representation is preserved as `represented_only` metadata; admission
never marks canonical coverage stale and never applies invalidation.

## Validation And Rejection

Admission requires an accepted AG-SEM-05 initial answer contract and an issued
authorized action with exact run/action/stage/observation binding. It recomputes
the `ContractAmendmentRecord` digest from the actual payload content and rejects
stale or tampered amendment payloads. It rejects authority/closed-surface taint on
the raw payload before reconstruction.

It validates exact parent/accepted contract binding, optional
`accepted_contract_ref` against `contract:{accepted_contract_version}:accepted`,
and trigger refs against `semantic_observation_admission_history`,
`component_coverage_history`, admitted content refs, and EvidenceLedger custody.
It rejects duplicate amendment record ids/digests and stale/replayed admissions,
and stores only sanitized, bounded, projection-safe fields.

## Closed Surfaces

No initial answer contract mutation, no coverage stale marking, no coverage
invalidation application, no SufficiencyJudgment behavior, no SearchJudgment /
QueryPlan / SearchWorkPlan / follow-up behavior, no FinalAnswerPacket or Author
behavior, no provider/search/retrieval/fetch/read behavior, no citation behavior,
no live validation, and no `core/pipeline_orchestrator.py` changes (expected
delta 0).

## Relationship To Prior AG-SEM Phases

- Consumes AG-SEM-05 accepted initial answer contract
- Consumes AG-SEM-06 admitted `SemanticObservation` history for trigger refs
- Consumes AG-SEM-07 reduced component coverage history for trigger refs
- Consumes AG-SEM-04 passive `ContractAmendmentRecord` proposal schema
- Does not apply or accept amendments into contract authority

## Validation

New tests are classified as `phase_focus` and are not added to `fast_pr` in this
phase.

- `tests/test_ag_sem_08_contract_amendment_admission.py`
- `tests/test_ag_sem_01_passive_semantic_contract_foundation.py` through
  `tests/test_ag_sem_07_component_coverage_reduction.py`
- `tests/test_run_kernel_ag91h.py`
- touched-file `ruff check`, `pre-commit`, and `git diff --check`
