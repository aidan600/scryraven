Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96I3M1_EVIDENCE_LEDGER_INTAKE_ADAPTER).

# AG-96I3M1 EvidenceLedger Intake Adapter

## Status

AG-96I3M1 adds a narrow, pure, offline intake adapter:

```text
core.evidence_ledger_intake_adapter
```

It proves the first half of the AG-96I3M bridge:

```text
AG-96I3L admission-review-ready candidate
+ explicit intake binding object
-> EvidenceLedgerObservation / reducer payload
-> RunKernel-governed EvidenceLedger mutation in offline tests
```

This is not runtime activation. AG-96I3M2 must choose and wire exactly one
runtime consumer before product flow can use this path.

## Binding Boundary

AG-96I3L diagnostic readiness is necessary but not sufficient for intake. The
adapter requires caller-supplied binding facts that AG-96I3L does not invent:

- `requirement_id`
- `candidate_id`
- `observation_id` or `observation_ref`
- `source_obligation`
- `required_source_class`, `required_source_tier`, and `required_currentness`
- explicit `official_current_rules` mapping for official-current obligations
- `origin_phase`, `origin_action`, `origin_record_type`, and
  `origin_schema_version`
- `idempotency_key` or `deduplication_basis`
- downstream flags kept false: `final_evidence`, `citation_eligible`, and
  `author_activation_allowed`

The initial supported source obligation is `official_current`, with an explicit
mapping into `official_current_rules`, `official`, and `current`.

## Reducer Shape

A valid adapter result emits `EvidenceLedgerObservation` with:

- one source requirement bound to the explicit `requirement_id`;
- one candidate bound to the explicit `candidate_id`;
- one requirement link between them;
- candidate `record_kind=fact` and `disposition=accepted`;
- `final_evidence_eligible=false`;
- no `final_evidence` list.

Offline tests reduce this payload through:

```text
RunKernel.authorize_evidence_ledger_reduction
-> core.evidence_ledger_runtime.execute_evidence_ledger_reduction_action
-> RunKernel.reduce
-> RunState.evidence_ledger.reduce_observation
```

The canonical `RunState.evidence_ledger` mutates, and the official-current
projection records the requirement as satisfied when the explicit mapping and
candidate facts match.

## Idempotency

`EvidenceLedger.reduce_observation` now treats repeated explicit
`observation_id` values as already reduced and returns without appending a second
observation, custody record, candidate, requirement, or link. Distinct
observation IDs keep the existing reduction behavior.

## Closed Surfaces Preserved

AG-96I3M1 does not change provider routing, provider selection, provider depth,
query generation, query ordering, retrieval ranking/filtering, SearchWorkPlan,
QueryPlan, citations, SufficiencyJudgment, FinalAnswerPacket, Author behavior,
prompts, live provider/search/model/fetch/read calls, or
`core/pipeline_orchestrator.py` product domain logic.

The adapter rejects or blocks non-ready AG-96I3L candidates, candidates with
blockers, missing binding IDs, unsupported obligations, missing
official-current mapping, downstream activation flags, and raw/private payload
retention attempts.
