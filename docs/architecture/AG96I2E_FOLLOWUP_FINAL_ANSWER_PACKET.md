# AG-96I2E Follow-up FinalAnswerPacket Preparation

## Status

AG-96I2E opens only fixture-only FinalAnswerPacket preparation after the
AG-96I2D sufficiency recheck:

```text
RunKernel.followup_sufficiency_recheck_state
+ RunKernel.sufficiency_judgment_projection
+ RunKernel.EvidenceLedger projection
+ RunKernel.followup_evidence_intake_state
-> authorized follow-up FinalAnswerPacket preparation action
-> fixture-only packet adapter derives packet authority from canonical state
-> RunKernel reducer commits followup packet state/projection/history
-> RunKernel.final_answer_packet and final_answer_authority_projection updated
-> Author execution remains deferred
```

This phase is more than trace or projection because RunKernel consumes the
authorized packet observation and updates the existing canonical
`FinalAnswerPacket` state path. It is still less than user-visible answering.

## Runtime Records

The records live in `core.followup_final_answer_packet_runtime` and are
schema-versioned as `followup_final_answer_packet_ag96i2e_v1`:

- `FollowupFinalAnswerPacketRequest`;
- `FollowupFinalAnswerPacketResult`;
- `FollowupFinalAnswerPacketObservation`;
- `FollowupFinalAnswerPacketConsumptionRecord`.

They bind the AG-96I2A authorization consumption, AG-96I2B fixture execution,
AG-96I2C EvidenceLedger intake, AG-96I2D sufficiency recheck, provider-job kind,
component and source-obligation links, requirement IDs, expected source classes,
EvidenceLedger projection digest, SufficiencyJudgment digest, recheck digest,
fixture-only provenance, and no-live/no-Author/no-citation-rendering posture.

## RunKernel Consumption

RunKernel owns the new authorization and reducer seam:

```text
RunKernel.authorize_followup_final_answer_packet_prepare(...)
-> execute_followup_final_answer_packet_prepare_action(...)
-> RunKernel.reduce(...)
-> RunState.followup_final_answer_packet_state/projection/history
-> RunState.final_answer_packet
-> RunState.final_answer_authority_projection
```

Caller inputs are merged first and canonical binding fields are applied last.
The reducer treats the observation payload as untrusted: it validates binding
identity from the observation, then re-derives the packet from the authorized
action inputs, canonical recheck state, canonical SufficiencyJudgment projection,
canonical EvidenceLedger projection, and canonical intake state.

## FinalAnswerPacket Path

AG-96I2E does not create a parallel packet owner. The adapter uses the existing
`FinalAnswerPacket` model and `build_final_answer_packet(...)` packet builder,
then RunKernel commits the derived packet projection into the existing
`RunState.final_answer_packet` and `RunState.final_answer_authority_projection`
path.

The follow-up packet state links back to the canonical packet projection through
`canonical_final_answer_packet_ref`. The Author payload status is
`author_execution_deferred`, so `RunKernel.authorize_author_execution(...)`
continues to fail closed.

## Packet Derivation

Packet-level evidence references are derived from canonical EvidenceLedger
custody. A fixture-success candidate can become packet-level eligible evidence
only when it is accepted in ledger custody, satisfies the rechecked source
requirement, and matches the expected source class. Bridge-only, no-result,
wrong-source-class, error, contextual, unreadable, or rejected candidates remain
ineligible.

Packet-level citation eligibility metadata is allowed in this phase. It is
derived from the packet evidence records and SufficiencyJudgment constraints.
AG-96I2E does not format citations, render citations, reorder citations for
prose, or change Author citation behavior.

The packet carries SufficiencyJudgment-derived readiness posture, mandatory
caveats, prohibited upgrades, missing obligations, source-bound unknowns,
unresolved conflict posture, fixture-only provenance, and an Author-facing
authority payload marked as fixture-only and not for product answer activation.

## Closed Surfaces

AG-96I2E does not open:

- AuthorExecutor invocation;
- Author prompt or prose changes;
- user-visible product final-answer behavior;
- citation formatting or rendering;
- live providers;
- search;
- retrieval;
- fetch/read;
- model calls;
- provider-job executors;
- provider routing, selection, depth, or query generation;
- retrieval ranking/filtering;
- SearchJudgment re-evaluation;
- conversational Follow-up Turn Contract behavior;
- `core/pipeline_orchestrator.py` domain logic.

The canonical packet records preserve:

- `final_answer_packet_prepared: true`;
- `author_activation_allowed: false`;
- `author_execution_deferred: true`;
- `citation_rendering_changed: false`;
- `citation_formatter_invoked: false`;
- `product_answer_behavior_changed: false`;
- `live_validation_not_run: true`;
- `provider_execution_licensed: false`.

## Follow-on AG-96I2F

AG-96I2F is now documented in
[AG96I2F_FOLLOWUP_AUTHOR_GATE.md](AG96I2F_FOLLOWUP_AUTHOR_GATE.md). It opens
only fixture-only Author gate / packet consumption and keeps Author execution,
Author prose, citation rendering, and product final-answer behavior closed.

AG-96I2G or a later phase is required for either a fixture Author observation or
product-answer activation. Any later activation must explicitly license Author
invocation, prompt/prose behavior, citation rendering or formatting behavior if
changed, and product final-answer activation.
