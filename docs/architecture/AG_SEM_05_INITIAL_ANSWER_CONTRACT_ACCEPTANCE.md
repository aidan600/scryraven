# AG-SEM-05 Canonical Initial Answer-Component Acceptance

Status: Canonical authority bridge. First canonical semantic authority bridge.

## Proof Class

`offline_product_path_proof`, qualified as a canonical RunKernel reducer proof
only. This is not ordinary semantic producer activation and must not be described
as ordinary product-path completion.

## Scope

AG-SEM-05 adds the first canonical semantic authority bridge. A
RunKernel/RunAuthority-authorized reducer may accept exactly one validated passive
`QuestionMeaningRecord` / answer-component proposal (AG-SEM-01) and create
canonical initial answer-component contract state owned by RunKernel.

The product-path delta is limited to RunKernel canonical state. Given an
authorized action and a validated passive proposal, RunKernel creates canonical
initial answer-component contract state with exact component IDs, revisions,
digests, parent proposal binding, lineage, projection, and history. Ordinary
product execution does not yet create these semantic records by itself; the
bridge condition is a future ordinary semantic producer vertical slice.

## Actual App Delta

- New bounded runtime module `core/initial_answer_contract_acceptance_runtime.py`
  builds and validates the canonical acceptance state and its projection. It does
  not import `core.run_kernel`, keeping the import graph acyclic.
- `core/run_kernel.py` gains:
  - action type `ActionType.INITIAL_ANSWER_CONTRACT_ACCEPT`
    (`"initial_answer_contract_accept"`)
  - observation type `ObservationType.INITIAL_ANSWER_CONTRACT_ACCEPTED`
    (`"initial_answer_contract_accepted"`)
  - stage `INITIAL_ANSWER_CONTRACT_ACCEPTANCE_STAGE`
    (`"initial_answer_contract_acceptance"`)
  - `RunState` fields `initial_answer_contract`,
    `initial_answer_contract_projection`, and `initial_answer_contract_history`
    (mirrored into `KernelTraceProjection`)
  - authorization helper
    `RunKernel.authorize_initial_answer_contract_acceptance(...)` which binds the
    parent `QuestionMeaningRecord` id, the parent proposal digest, and the
    request id into the authorized action
  - a reducer branch that builds canonical state, projection, and history.

## Runtime Consumer

The RunKernel reducer/state/projection is the runtime consumer. The acceptance
moves initial answer-component contract state from passive proposal (AG-SEM-01)
into RunKernel-owned canonical state.

## Required Canonical State

The canonical state records the schema/version identifier, `run_id`,
`request_id`, the authorized action id, the accepted contract version, a
deterministic accepted-contract digest, the parent `QuestionMeaningRecord` id and
digest, the parent proposal schema version, the accepted answer-component refs
(component id, revision, digest, requirement posture, materiality, already-present
source-obligation refs/candidates, allowed support kinds, mandatory caveats, and
prohibited upgrades), compact accepted semantic slot refs (slot id, kind, status,
materiality, selected value only when already selected by the proposal, and an
`unresolved_material` flag), the materiality policy projection when already
present in the proposal, and lineage (`created_by`, `created_from`, parent
proposal digest, reducer action id). The projection carries no raw or private
data.

## Required Semantics

The reducer accepts the initial answer contract only. It does not interpret the
question, invent answer components, resolve material ambiguity, add assumptions,
remove or weaken requirements, create coverage, create amendments, decide
Sufficiency, authorize follow-up, or create Author input. Material ambiguity in
the proposal is preserved as unresolved or ambiguous and is never resolved.

This phase proves a real canonical RunKernel reducer/authority bridge, not a
mere passive schema. It does not prove ordinary semantic producer activation.

## Validation And Rejection

Acceptance requires an issued authorized action with matching `run_id` and
`action_id`, rejects duplicate reduction (the already-reduced action and a second
acceptance after canonical state exists), rejects stale or mismatched action
bindings, requires a valid passive proposal payload, requires exact parent
proposal id and digest binding, rejects missing or empty answer components,
rejects missing component id/revision/digest, rejects duplicate component refs,
and rejects wrong run/request/proposal/action binding. The acceptance creates
canonical state, projection, and history only for this stage and leaves
Sufficiency, FinalAnswerPacket, Author, SearchJudgment, QueryPlan, coverage,
SemanticObservation admission, and amendment state unchanged.

## Closed Surfaces

This phase does not add SemanticObservation admission, a ComponentCoverageRecord
reducer, a ContractAmendmentRecord reducer, SufficiencyJudgment behavior,
SearchJudgment / QueryPlan / SearchWorkPlan / follow-up behavior,
FinalAnswerPacket behavior, Author payload/prompt/prose/execution/finalization
behavior, provider/search/retrieval/fetch/read behavior, or citation behavior.

No live validation is allowed. `core/pipeline_orchestrator.py` is unchanged
(expected delta 0).

## Relationship To AG-SEM-01..04

AG-SEM-05 consumes the AG-SEM-01 passive `QuestionMeaningRecord` by id and digest
and binds its answer components by component id, revision, and digest. It does not
admit AG-SEM-02 SemanticObservation, reduce AG-SEM-03 ComponentCoverageRecord, or
accept AG-SEM-04 ContractAmendmentRecord. Those remain closed and are the subject
of later canonical bridges.

## Validation

New tests are classified as `phase_focus` and are not added to `fast_pr` in this
phase. Phase validation includes the AG-SEM-05 focused test, the immediate
AG-SEM-01/02/03/04 producer-contract tests, the AG-91H RunKernel spine test,
touched-file lint/format checks, pre-commit for touched files, and
`git diff --check`.
