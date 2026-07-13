Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96I2C_FOLLOWUP_EVIDENCE_INTAKE).

# AG-96I2C Follow-up EvidenceLedger Intake

## Status

AG-96I2C opens only fixture-origin EvidenceLedger intake after AG-96I2B:

```text
RunKernel.followup_execution_state
-> authorized follow-up EvidenceLedger intake action
-> fixture-only intake adapter validates execution binding and fixture status
-> EvidenceLedger receives sanitized fixture-origin custody/intake observation
-> RunKernel reduces canonical followup_evidence_intake_state
-> SufficiencyJudgment recheck remains deferred
```

This phase is more than trace or projection because the runtime reducer mutates
`RunState.evidence_ledger` through the canonical `EvidenceLedger.reduce_observation`
API. It is still less than sufficiency or answer activation.

## Runtime Records

The records live in `core.followup_evidence_intake_runtime` and are
schema-versioned as `followup_evidence_intake_ag96i2c_v1`:

- `FollowupEvidenceIntakeRequest`;
- `FollowupEvidenceIntakeResult`;
- `FollowupEvidenceIntakeObservation`;
- `FollowupEvidenceIntakeConsumptionRecord`.

They preserve run/checkpoint identity, AG-96I2A authorization consumption,
sealed candidate identity, AG-96I2B execution and observation identity,
provider-job kind, component and source-obligation links, fixture result status,
bridge-only posture, expected EvidenceLedger custody update, sanitized fixture
summary, fixture-only provenance, and no-live boundary flags.

## RunKernel Consumption

RunKernel owns the new authorization and reducer seam:

```text
RunKernel.authorize_followup_evidence_intake(...)
-> execute_followup_evidence_intake_action(...)
-> RunKernel.reduce(...)
-> RunState.evidence_ledger.reduce_observation(...)
-> RunState.followup_evidence_intake_state
-> RunState.followup_evidence_intake_projection
-> RunState.followup_evidence_intake_history
```

Caller inputs cannot override canonical binding fields from
`RunState.followup_execution_state`, including execution id, observation id,
sealed candidate id, authorization consumption id, fixture mode,
provider-job kind, component id, source-obligation id, result status,
provider-execution license posture, and intake mode.

The reducer accepts only fixture-only intake observations. It rejects live
provider/search/retrieval/fetch/model flags, provider-job scheduling/dispatch,
query-generation changes, ranking/filtering changes, sufficiency rechecks,
search re-runs, FinalAnswerPacket updates, citation behavior changes, Author
behavior changes, and pipeline-orchestrator domain logic changes.

## EvidenceLedger Mutation

AG-96I2C does not invent a parallel ledger. The intake adapter builds a
sanitized `EvidenceLedgerObservation`, and RunKernel mutates the existing
`RunState.evidence_ledger` with `EvidenceLedger.reduce_observation(...)`.
The reducer derives the actual ledger mutation payload from canonical
follow-up execution/intake binding fields before mutation, so caller-supplied
ledger requirement, candidate, link, or final-evidence fields cannot upgrade a
bridge-only, failed, wrong-class, or off-contract fixture result.

The fixture-origin custody record is visibly tied to:

- `component_id`;
- `source_obligation_id`;
- `provider_job_kind`;
- `sealed_candidate_id`;
- follow-up execution id and observation id;
- sanitized fixture result summary.

`fixture_success` may admit a fixture-origin candidate custody record into the
ledger only when the fixture candidate's source class matches the sealed
candidate's expected source-obligation contract. The required ledger source
class is derived from the sealed `expected_evidence_ledger_custody_update`
source classes, with sealed provider-job kind as a fallback when sanitized
payload depth redaction obscures the nested class list. The fixture result's
`source_class` describes the candidate; it does not redefine the requirement.
This intake does not set final evidence satisfied, does not create final-answer
citation eligibility, and does not update FinalAnswerPacket or Author state.

`fixture_bridge_only` records bridge-only posture but cannot satisfy source
obligations, final evidence, or citation eligibility.

`fixture_no_result`, `fixture_wrong_source_class`, and `fixture_error` record
failure/no-admission posture and do not create satisfying EvidenceLedger
evidence.

## Closed Surfaces

AG-96I2C still does not open:

- live providers;
- search;
- retrieval;
- fetch/read;
- model calls;
- provider-job executors;
- provider routing, selection, depth, or query generation;
- retrieval ranking/filtering;
- SufficiencyJudgment recheck;
- SearchJudgment re-evaluation;
- FinalAnswerPacket updates;
- citation eligibility or final citation behavior;
- Author prompt, prose, or final-answer behavior;
- conversational Follow-up Turn Contract behavior;
- `core/pipeline_orchestrator.py` domain logic.

## Follow-on AG-96I2D

AG-96I2D is expected to perform the fixture-only SufficiencyJudgment recheck
over the updated EvidenceLedger state. That later phase should decide how
fixture-origin custody affects sufficiency without changing live provider,
search, retrieval, citation, FinalAnswerPacket, or Author behavior by
implication.

AG-96I2D is now documented in
[AG96I2D_FOLLOWUP_SUFFICIENCY_RECHECK.md](AG96I2D_FOLLOWUP_SUFFICIENCY_RECHECK.md).
