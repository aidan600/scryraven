Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96I2D_FOLLOWUP_SUFFICIENCY_RECHECK).

# AG-96I2D Follow-up Sufficiency Recheck

## Status

AG-96I2D opens only the fixture-only SufficiencyJudgment recheck after
AG-96I2C EvidenceLedger intake:

```text
RunKernel.followup_evidence_intake_state
+ RunKernel.EvidenceLedger projection
+ prior SufficiencyJudgment or sufficiency handoff posture when present
-> authorized follow-up sufficiency recheck action
-> bounded fixture-only recheck adapter
-> RunKernel reducer derives canonical outcome from current state
-> RunState.followup_sufficiency_recheck_state/projection/history
-> RunState.sufficiency_judgment/projection/history through the existing path
-> FinalAnswerPacket remains deferred
```

The phase is more than trace/projection because the intended runtime consumer,
RunKernel, consumes the recheck action and updates canonical SufficiencyJudgment
state. It is still less than final-answer activation.

## Runtime Records

The records live in `core.followup_sufficiency_recheck_runtime` and are
schema-versioned as `followup_sufficiency_recheck_ag96i2d_v1`:

- `FollowupSufficiencyRecheckRequest`;
- `FollowupSufficiencyRecheckResult`;
- `FollowupSufficiencyRecheckObservation`;
- `FollowupSufficiencyRecheckConsumptionRecord`.

They preserve run/checkpoint identity, AG-96I2A authorization consumption,
AG-96I2B fixture execution identity, AG-96I2C EvidenceLedger intake identity,
provider-job kind, component and source-obligation links, requirement IDs,
expected source classes, EvidenceLedger projection digest, source requirement
statuses, custody gaps, fixture-only provenance, no-live/no-provider/no-search/
no-fetch/no-model posture, and explicit FinalAnswerPacket/Author/citation
deferral.

## RunKernel Consumption

RunKernel owns the new authorization and reducer seam:

```text
RunKernel.authorize_followup_sufficiency_recheck(...)
-> execute_followup_sufficiency_recheck_action(...)
-> RunKernel.reduce(...)
-> RunState.followup_sufficiency_recheck_state/projection/history
-> RunState.sufficiency_judgment/projection/history
```

Caller inputs are merged first and canonical binding fields are applied last.
The reducer treats observation payloads as untrusted: it validates binding
identity from the observation, then re-derives the canonical recheck record from
the AuthorizedAction inputs, current follow-up intake state, current
EvidenceLedger projection, and existing sufficiency posture. Observation-supplied
claims that would activate Author, FinalAnswerPacket, citations, or direct
answer readiness are overwritten by canonical fixture-only deferral.

## SufficiencyJudgment Path

AG-96I2D does not create a parallel sufficiency authority. The recheck adapter
uses the existing AG-92C deterministic SufficiencyJudgment API over a narrow
fixture-only recheck input, and RunKernel commits the resulting projection
through the same canonical SufficiencyJudgment projection builder used by the
existing reducer path.

Fixture-origin EvidenceLedger satisfaction may improve the fixture-only posture
to `ready_for_next_fixture_phase`, but the state still records:

- `final_answer_packet_deferred: true`;
- `author_activation_allowed: false`;
- `citation_behavior_changed: false`;
- `live_validation_not_run: true`.

Bridge-only, no-result, wrong-source-class, error, unresolved conflict, and
source-bound-unknown postures remain non-sufficient for product answer
activation.

## Closed Surfaces

AG-96I2D does not open:

- live providers;
- search;
- retrieval;
- fetch/read;
- model calls;
- provider-job executors;
- provider routing, selection, depth, or query generation;
- retrieval ranking/filtering;
- SearchJudgment re-evaluation;
- FinalAnswerPacket creation or update;
- citation eligibility or final citation behavior;
- Author prompt, prose, or final-answer behavior;
- conversational Follow-up Turn Contract behavior;
- `core/pipeline_orchestrator.py` domain logic.

AG-96I2E or a later phase is required to decide whether and how a rechecked
SufficiencyJudgment can feed FinalAnswerPacket preparation.

AG-96I2E is now documented in
[AG96I2E_FOLLOWUP_FINAL_ANSWER_PACKET.md](AG96I2E_FOLLOWUP_FINAL_ANSWER_PACKET.md).
