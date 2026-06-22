# AG-SEM-02 Sanitized Content Reference And SemanticObservation

Status: Passive schema/design record.

## Proof Class

`schema_or_passive_record`

## Scope

AG-SEM-02 adds passive records in
`core/semantic_observation_foundation.py` for:

- sanitized, bounded, evidence-bound content references; and
- passive `SemanticObservation` proposals over those content references.

No product path behavior changes in this phase. There is no runtime consumer in
this phase.

## New Record Types

- `SanitizedContentReference`: bounded sanitized content tied to an evidence ref,
  answer component ref, optional question-meaning ref or digest, bounded source
  metadata, locator metadata, extraction metadata, deterministic content digest,
  and explicit retention-safe posture.
- `SemanticObservation`: passive proposal describing candidate support,
  contradiction, qualification, missing facts, normalization, computation,
  caveat candidates, follow-up gap candidates, or candidate amendment notes for
  one answer component and one contract/component version posture.
- Collection validators that reject duplicate content refs, duplicate refs inside
  observations, missing support-bearing content refs, and component/contract
  mismatches between observations and content refs.

## Relationship To AG-SEM-01

AG-SEM-02 references AG-SEM-01 `QuestionMeaningRecord` and
`AnswerComponentContract` only by stable IDs, revisions, and digests. It does not
import AG-SEM-01 records, embed semantic slots, embed answer components, accept a
contract, or mutate contract state.

## Closed Surfaces

This phase does not change RunKernel, RunAuthority reducers, EvidenceLedger
admission, SearchJudgment, SufficiencyJudgment, FinalAnswerPacket, Author
execution, pipeline orchestration, QueryPlan or SearchWorkPlan runtime behavior,
provider/search/fetch/read/retrieval behavior, citation behavior, prompts, or
product output.

No live validation is allowed.

## Non-Proofs

AG-SEM-02 does not create canonical coverage, a canonical observation admission
reducer, ComponentCoverageRecord, ContractAmendmentRecord, SufficiencyJudgment
consumption, SearchJudgment follow-up consumption, FinalAnswerPacket authority,
Author-facing semantic authority, provider/search behavior, prompt behavior, or
live proof.

## Bridge

A later AG-SEM phase may add a canonical observation admission reducer that
validates `SemanticObservation` records against exact contract/component version,
EvidenceLedger custody refs, sanitized content refs, authorization, and retention
posture before any canonical coverage reducer may consume them.

## Validation

Phase validation should include the AG-SEM-02 focused test, AG-SEM-01 passive
semantic contract tests, `fast_pr`, ruff checks, and `git diff --check`.
