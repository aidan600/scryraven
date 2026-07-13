Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG_SEM_03_COMPONENT_COVERAGE_RECORD).

# AG-SEM-03 ComponentCoverageRecord Schema

Status: Passive schema/design record.

## Proof Class

`schema_or_passive_record`

## Scope

AG-SEM-03 adds the passive `ComponentCoverageRecord` schema in
`core/component_coverage_record.py`. The record is a future per-answer-component
semantic support scoreboard. It records exact contract/component bindings,
EvidenceLedger snapshot binding, accepted SemanticObservation refs, sanitized
answer-bearing content refs, custody/source-obligation/content availability
posture, semantic support posture, direct/inferred/computed support posture,
normalization and assumption posture, conflict/currentness posture, remaining
unknowns, caveats, prohibited upgrades, follow-up posture, version validity,
lineage, and a deterministic record digest.

No product path behavior changes in this phase. There is no runtime consumer in
this phase.

## New Record Types

- `ComponentCoverageRecord`: passive per-component coverage scoreboard with
  categorical states: `unassessed`, `unsupported`, `partial`,
  `supported_with_caveats`, `satisfied`, `conflicted`, `blocked`, and `stale`.
- `EvidenceLedgerSnapshotBinding`: exact EvidenceLedger schema/version/digest
  and custody binding for the coverage record.
- `SemanticObservationCoverageRef`: accepted SemanticObservation identity,
  digest, component revision, component digest, support status, support posture,
  and content refs.
- `ContentReferenceCoverageBinding`: sanitized content-reference identity,
  digest, evidence ref, component revision, component digest, answer-bearing
  flag, and availability posture.
- `CoverageLineage`: deterministic passive lineage. Reducer and runtime
  consumption remain false in AG-SEM-03.

## Required Invariants

`satisfied` coverage is rejected unless it has supported semantic observations,
answer-bearing content refs, EvidenceLedger custody, valid contract/component
and EvidenceLedger versions, satisfied or not-applicable source obligations,
available content, no unresolved conflict, current or not-time-sensitive
currentness posture, no remaining unknowns, and no required follow-up.

`satisfied` coverage cannot arise solely from IDs or digests, EvidenceLedger
custody, candidate discovery, search snippets, provider answer products, work
attempted/completed, a missing answer-bearing content ref, observations bound to
another component revision, stale versions, or unsupported inferred/computed
claims. Diagnostic scores are explicitly non-authoritative.

## Relationship To AG-SEM-01 And AG-SEM-02

AG-SEM-03 references AG-SEM-01 answer components by component ID, revision, and
digest, and references AG-SEM-02 SemanticObservation and sanitized content
records by IDs and digests. It does not embed semantic slots, duplicate
SemanticObservation content, admit observations, reduce canonical coverage, or
mutate the accepted contract.

## Closed Surfaces

This phase does not change RunKernel canonical reducers, SemanticObservation
admission, EvidenceLedger admission, SearchJudgment, QueryPlan, SearchWorkPlan,
follow-up loops, SufficiencyJudgment consumption, FinalAnswerPacket,
Author-facing payloads, pipeline orchestration, provider/search/fetch/read/
retrieval behavior, citation behavior, prompts, or product output.

No live validation is allowed.

## Non-Proofs

AG-SEM-03 does not create canonical coverage, implement the future reducer,
prove SufficiencyJudgment behavior, activate follow-up behavior, change final
answer behavior, prove provider/search behavior, or create live product proof.

## Bridge

A later RunKernel-authorized reducer may consume accepted SemanticObservations,
EvidenceLedger custody, source-obligation state, sanitized content references,
and exact contract/component bindings to create canonical component coverage.
That reducer is closed in AG-SEM-03.

## Validation

New tests are classified as `phase_focus` and are not added to `fast_pr` in this
phase. Phase validation should include the AG-SEM-03 focused test, immediate
AG-SEM-01/02 producer-contract tests, touched-file lint/format checks, and
`git diff --check`.
