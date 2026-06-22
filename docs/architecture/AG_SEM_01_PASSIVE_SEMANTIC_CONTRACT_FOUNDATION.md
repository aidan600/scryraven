# AG-SEM-01 Passive Semantic Contract Foundation

Status: Passive schema/design record.

## Proof Class

`schema_or_passive_record`

## Scope

AG-SEM-01 adds passive semantic-contract foundation records in
`core/semantic_contract_foundation.py`. The records describe a proposed
`QuestionMeaningRecord`, semantic slots, answer-component contracts, contract
lineage, materiality policy, and passive references to existing query-shape and
work-planning records.

No product path behavior changes in this phase. There is no runtime consumer in
this phase.

## New Record Types

- `SemanticSlot`: bounded representation of user-question meaning variables
  such as entity, metric, time period, geography, configuration, load factor, or
  direct-vs-computed basis.
- `AnswerComponentContract`: proposed answer component requirements, accepted
  support kinds, slot refs, dependencies, caveats, and prohibited upgrades.
- `QuestionMeaningRecord`: passive proposal envelope with request identity,
  resolver posture, slots, components, materiality status, lineage, and digest.
- `ContractLineage`: passive version and proposal digest fields. Accepted fields
  remain absent or null.
- `MaterialityPolicy`: records material choices that require confirmation and
  non-material additions that may be represented later without auto-acceptance.
- `QueryShapeAssessmentRef` and `SearchWorkPlanRef`: relationship records only.

## Relationship To Existing Records

`QueryShapeAssessment` may seed a passive `QuestionMeaningRecord` through a
sanitized reference. That reference is trace-only and is not promoted to accepted
authority.

`SearchWorkPlan` remains work planning only. It may later use accepted answer
component refs for planning, but the answer-component contract remains the
proposed answer-authority shape. `SearchWorkPlan` must not mark semantic
satisfaction or become the semantic owner.

## Closed Surfaces

This phase does not change RunKernel, RunAuthority runtime behavior,
SufficiencyJudgment, FinalAnswerPacket, Author execution, pipeline orchestration,
query planning, provider/search/retrieval behavior, citation behavior, prompts,
or product output.

No live validation is allowed.

## Bridge

A later canonical reducer phase may accept versioned answer components into the
ordinary RunAuthority chain after passive schemas and invariants are stable.
AG-SEM-01 does not create canonical coverage, semantic observation,
sufficiency, amendment, or Author authority.

## Validation

Phase validation should include the AG-SEM-01 focused test, existing passive
query-shape and SearchWorkPlan tests, `fast_pr`, ruff checks, and `git diff
--check`.
