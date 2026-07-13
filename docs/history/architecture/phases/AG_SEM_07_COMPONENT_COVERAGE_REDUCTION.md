Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG_SEM_07_COMPONENT_COVERAGE_REDUCTION).

# AG-SEM-07 Canonical ComponentCoverageRecord Reduction

Status: Canonical authority bridge. Third canonical semantic authority bridge.

## Proof Class

`offline_product_path_proof`, qualified as a canonical RunKernel reducer proof
only. This is not ordinary semantic producer activation and must not be described
as ordinary product-path completion.

## Scope

AG-SEM-07 lets a RunKernel/RunAuthority-authorized reducer reduce exactly one
validated passive `ComponentCoverageRecord` proposal (AG-SEM-03) into canonical
RunKernel-owned per-component coverage state.

The product-path delta is limited to RunKernel canonical state. Given an authorized
action, an accepted AG-SEM-05 initial answer contract, at least one admitted
AG-SEM-06 `SemanticObservation`, valid EvidenceLedger custody projection, and a
valid passive `ComponentCoverageRecord`, RunKernel creates canonical component
coverage state, projection, and history.

This phase reduces coverage only. It does not consume coverage in Sufficiency,
amend the contract, decide SearchJudgment, activate QueryPlan/SearchWorkPlan,
authorize follow-up, create Author input, change search/provider behavior, or
change final-answer or citation behavior.

Ordinary product execution does not yet create these semantic records by itself;
the bridge condition is a future ordinary semantic producer vertical slice.

## Actual App Delta

- New bounded runtime module `core/component_coverage_reduction_runtime.py`
  builds and validates the canonical coverage state and its projection. It
  reuses the AG-SEM-03 `ComponentCoverageRecord` record and validators so the
  coverage digest and satisfied-coverage invariants stay consistent with the
  passive foundation. It does not import `core.run_kernel` or follow-up/Sufficiency
  runtime modules, keeping the import graph acyclic.
- `core/run_kernel.py` gains:
  - action type `ActionType.COMPONENT_COVERAGE_REDUCE`
    (`"component_coverage_reduce"`)
  - observation type `ObservationType.COMPONENT_COVERAGE_REDUCED`
    (`"component_coverage_reduced"`)
  - stage `COMPONENT_COVERAGE_REDUCTION_STAGE`
    (`"component_coverage_reduction"`)
  - `RunState` fields `component_coverage_state`, `component_coverage_projection`,
    and `component_coverage_history` (mirrored into `KernelTraceProjection`)
  - authorization helper `RunKernel.authorize_component_coverage_reduction(...)`
    which requires an accepted initial answer contract and at least one admitted
    observation, and binds coverage record id/digest, answer component
    id/revision/digest, and accepted contract digest/version into the authorized
    action
  - a reducer branch that builds canonical state, projection, and history.

## Runtime Consumer

The RunKernel reducer/state/projection is the immediate canonical consumer; the
intended downstream runtime consumer is a future Sufficiency coverage-consumption
reducer. The reduction moves a passive coverage record (AG-SEM-03) into
RunKernel-owned canonical coverage state without granting Sufficiency, Author, or
final-answer authority.

## Required Canonical State

The canonical coverage state records the schema/version identifier, owner,
`canonical_state` true, `trace_only`/`storage_only` false, `run_id`,
`request_id`, the authorized action id, the coverage record id and recomputed
coverage record digest, the accepted contract version and digest, the answer
component id, component revision and digest, coverage posture fields, accepted
observation refs, content reference bindings, evidence basis, normalization and
conflict/currentness postures, remaining unknowns, required caveats, prohibited
upgrades, follow-up need, mode budget posture, stale flag, evidence ledger
binding, a lineage block (`created_by`, `created_from`, `reducer_action_id`,
parent coverage record digest, accepted contract digest), a deterministic
`coverage_reduction_digest`, and closed-surface false flags (`sufficiency_decided`,
`final_answer_packet_created`, `author_input_created`, `amendment_created`,
`search_judgment_decided`, `query_plan_activated`, `search_work_plan_activated`,
`followup_authorized`, `citation_behavior_changed`,
`provider_search_behavior_changed`, `runtime_behavior_changed`, and
`live_validation_not_run` true). The projection carries no raw or private data.

## Required Semantics

The reducer reduces coverage only. Non-satisfied coverage may preserve caveats,
gaps, and unknowns without creating follow-up authority. Satisfied coverage
must fail closed on AG-SEM-03 invariants: semantic observation and answer-bearing
content basis, EvidenceLedger custody, supported semantic status, available
answer-bearing content, valid versions, and no unresolved conflict, remaining
unknowns, follow-up requirement, or exhausted/blocked mode budget.

AG-SEM-10 tightens the satisfied-coverage invariant: EvidenceLedger custody or
ID/digest presence is necessary but not sufficient. Satisfied coverage now also
requires coverage-bound evidence refs to be relevantly qualified by the current
EvidenceLedger projection, including accepted custody facts, readable/fetchable
candidate posture, final-evidence eligibility when marked, relevant requirement
links, source-obligation satisfaction, and official/current compatibility when
the accepted component carries a stronger source obligation. Partial,
unsupported, unknown, or insufficient coverage may still report weak evidence
honestly without claiming satisfied readiness.

For the compact completion status and next gates after AG-SEM-10, see
[`AG_SEM_05_10_COMPLETION_AND_NEXT_GATES.md`](AG_SEM_05_10_COMPLETION_AND_NEXT_GATES.md).

## Validation And Rejection

Reduction requires an accepted AG-SEM-05 initial answer contract, at least one
AG-SEM-06 admitted `SemanticObservation` relevant to the component, and an issued
authorized action with exact run/action/stage/observation binding. It recomputes
the `ComponentCoverageRecord` digest from the actual payload content and rejects
stale or tampered coverage payloads. It rejects authority/closed-surface taint on
the raw payload before reconstruction.

It validates exact contract binding, admitted observation refs (id/digest and
component bindings against `semantic_observation_admission_history`), and content
reference bindings backed only by admitted observations cited in the coverage
record (not merely any global admission history entry). It validates
EvidenceLedger binding via a local projection digest helper and a canonical
`snapshot_id` convention; satisfied coverage rejects only custody gaps relevant to
the coverage record's linked requirements or cited evidence refs. Satisfied
coverage also rejects evidence that is merely identity-present, stale,
unreadable, unfetchable, rejected, dropped, unqualified, lower-tier/contextual
against a stronger obligation, unlinked from the relevant source requirement, or
declared `source_obligation_status = not_applicable` when the accepted component
still carries source obligations.

It rejects duplicate coverage record ids/digests and stale/replayed reductions,
and stores only sanitized, bounded, projection-safe fields.

## Closed Surfaces

No ContractAmendmentRecord acceptance/reduction, no SufficiencyJudgment behavior,
no SearchJudgment / QueryPlan / SearchWorkPlan / follow-up behavior, no
FinalAnswerPacket or Author behavior, no provider/search/retrieval/fetch/read
behavior, no citation behavior, no live validation, and no
`core/pipeline_orchestrator.py` changes (expected delta 0).

This phase proves a real canonical RunKernel reducer/authority bridge, not a
mere passive schema. It does not prove ordinary semantic producer activation.

## Relationship To Prior AG-SEM Phases

- Consumes AG-SEM-05 accepted initial answer contract
- Consumes AG-SEM-06 admitted `SemanticObservation` history
- Consumes AG-SEM-03 passive `ComponentCoverageRecord` proposal schema
- Does not consume AG-SEM-04 `ContractAmendmentRecord`

## Validation

New tests are classified as `phase_focus` and are not added to `fast_pr` in this
phase.

- `tests/test_ag_sem_07_component_coverage_reduction.py`
- `tests/test_ag_sem_01_passive_semantic_contract_foundation.py` through
  `tests/test_ag_sem_06_semantic_observation_admission.py`
- `tests/test_run_kernel_ag91h.py`
- touched-file `ruff check`, `pre-commit`, and `git diff --check`
