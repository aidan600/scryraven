# AG-SEM-04 ContractAmendmentRecord Schema

Status: Passive schema/design record.

## Proof Class

`schema_or_passive_record`

## Scope

AG-SEM-04 adds the passive `ContractAmendmentRecord` schema in
`core/contract_amendment_record.py`. The record represents a proposed amendment
to an accepted semantic contract when semantic observation, evidence/content
state, coverage state, gaps, ambiguity, normalization needs, conflict, or
currentness indicate that a future contract change might be needed.

No product path behavior changes in this phase. There is no runtime consumer in
this phase.

## Actual App Delta

The app delta is limited to a passive schema, deterministic serialization and
record digest, categorical amendment operation/materiality/confirmation/
monotonicity/posture states, safe metadata handling, trace/projection helpers,
and validation invariants.

## New Record Types

- `ContractAmendmentRecord`: passive proposed amendment record bound to parent
  accepted contract version and digest.
- `AmendmentOperation`: typed operation with before/after or explicit operation
  payload.
- `AmendmentTriggerRefs`: refs to SemanticObservation, evidence, sanitized
  content, ComponentCoverageRecord, gap, conflict, or currentness triggers.
- `AffectedComponentRef`: component ID, revision, and digest scope binding.
- `CoverageInvalidationCandidateRef`: represented-only stale coverage or
  invalidation candidate. It never applies coverage invalidation.
- `AmendmentLineage`: passive lineage with no runtime consumption.

## Categorical States

Operation kinds are `add_component`, `revise_component`, `resolve_slot`,
`add_normalization`, `add_assumption`, `strengthen_source_obligation`,
`add_caveat`, `mark_irreducible_unknown`, `change_answer_posture`, and
`remove_or_weaken_requirement`.

Materiality states are `non_material`, `material`, and `unknown`.
Monotonicity states are `strengthens`, `preserves`, `weakens`, and `unknown`.
Disposition states are `proposed`, `requires_user_confirmation`,
`eligible_for_future_acceptance`, `rejected`, and `blocked`. AG-SEM-04 defines
no accepted disposition.

## Required Invariants

A valid record requires parent contract version and digest, at least one typed
operation, at least one trigger ref, and affected component ID/revision/digest
for component-changing operations.

Material entity, variant, metric, time-period, geography, configuration, load
factor, currency/inflation basis, or direct-vs-computed changes require user
confirmation or labeled scenario treatment. Removing or weakening a required
component, source obligation, acceptance criterion, source-bound posture, or
answer requirement requires explicit user authority and cannot be eligible for
automatic future acceptance.

Component-changing, material, revision/digest-changing, or weakening operations
must represent candidate stale coverage or candidate invalidated coverage refs.
`coverage_invalidation_applied` remains false.

The serialized record shows `passive=true`, `canonical_state=false`,
`accepted_authority=false`, `contract_mutation_applied=false`,
`coverage_invalidation_applied=false`, and `runtime_behavior_changed=false`.
Safe metadata scrubs sensitive keys such as raw prompts, raw provider payloads,
raw content, raw traces, private logs, DB rows, caches, secrets, tokens, and API
keys.

## Relationship To AG-SEM-01, AG-SEM-02, And AG-SEM-03

AG-SEM-04 binds to AG-SEM-01 answer components by component ID, revision, and
digest, and may reference the parent QuestionMeaningRecord or accepted contract
ref by ID/digest. It references AG-SEM-02 SemanticObservation and sanitized
content records only by safe refs. It references AG-SEM-03 ComponentCoverageRecord
state as a trigger or represented stale-coverage candidate. It does not embed or
change those records.

## Closed Surfaces

This phase does not change RunKernel canonical reducers, accepted contract
mutation, accepted contract version creation, actual coverage invalidation,
SemanticObservation admission, ComponentCoverageRecord reduction,
SufficiencyJudgment behavior, SearchJudgment, QueryPlan, SearchWorkPlan,
follow-up behavior, FinalAnswerPacket behavior, Author payloads or prose,
pipeline orchestration, provider/search/read/retrieval behavior, citation
behavior, prompts, or product output.

No live validation is allowed.

## Non-Proofs

AG-SEM-04 does not prove a canonical amendment reducer, contract mutation,
accepted contract version creation, coverage invalidation, SufficiencyJudgment
coverage consumption, follow-up activation, final-answer behavior, provider or
search behavior, citation behavior, or any live product behavior.

## Bridge

A later RunKernel-authorized canonical amendment reducer may consume accepted
amendment proposals, validate parent contract/component/evidence/coverage
bindings, create a new immutable contract version, and mark affected coverage
stale. That reducer is closed in AG-SEM-04.

## Validation

New tests are classified as `phase_focus` and are not added to `fast_pr` in this
phase. Phase validation should include the AG-SEM-04 focused test, immediate
AG-SEM-01/02/03 producer-contract tests, touched-file lint/format checks,
pre-commit for touched files, and `git diff --check`.
