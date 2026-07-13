Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96I2F_FOLLOWUP_AUTHOR_GATE).

# AG-96I2F Follow-up Author Gate

## Status

AG-96I2F opens only the fixture-only Author gate / Author-facing packet
consumption seam after AG-96I2E:

```text
RunKernel.followup_final_answer_packet_state
+ RunKernel.final_answer_packet
+ RunKernel.final_answer_authority_projection
-> authorized follow-up Author gate action
-> fixture-only Author gate adapter consumes FinalAnswerPacket authority
-> RunKernel reducer commits followup_author_gate_state/projection/history
-> Author execution remains blocked/deferred
```

This phase is more than trace or projection because the intended runtime
consumer, the Author-side gate adapter, reads packet-derived authority before
RunKernel reduces canonical gate state. It is still less than Author execution.

## Runtime Records

The records live in `core.followup_author_gate_runtime` and are
schema-versioned as `followup_author_gate_ag96i2f_v1`:

- `FollowupAuthorGateRequest`;
- `FollowupAuthorGateResult`;
- `FollowupAuthorGateObservation`;
- `FollowupAuthorGateConsumptionRecord`.

They bind the AG-96I2A authorization consumption, AG-96I2B fixture execution,
AG-96I2C EvidenceLedger intake, AG-96I2D sufficiency recheck, AG-96I2E packet
preparation, packet id, provider-job kind, component and source-obligation
links, requirement IDs, expected source classes, FinalAnswerPacket digest,
FinalAnswerPacket authority projection digest, fixture-only provenance, and
closed Author/citation/product-answer posture.

## RunKernel Consumption

RunKernel owns the new authorization and reducer seam:

```text
RunKernel.authorize_followup_author_gate(...)
-> execute_followup_author_gate_action(...)
-> RunKernel.reduce(...)
-> RunState.followup_author_gate_state/projection/history
```

Caller inputs are merged first and canonical binding fields are applied last.
The reducer treats the observation payload as untrusted: it validates the
authorized binding and then re-derives the canonical Author gate record from the
AuthorizedAction inputs, current follow-up FinalAnswerPacket state, current
`RunState.final_answer_packet`, and current
`RunState.final_answer_authority_projection`.

## Packet Authority Consumption

The Author gate consumes FinalAnswerPacket-derived authority, including:

- readiness status and `final_answer_allowed`;
- mandatory caveats and prohibited upgrades;
- missing, partial, and satisfied source obligations;
- source-bound numeric unknown posture;
- unresolved conflict posture carried by the packet preparation record;
- citation eligibility refs and eligible source IDs;
- the packet-derived Author payload ref in
  `final_answer_authority_projection`.

The gate records `packet_authority_consumed: true`, an
`author_gate_decision` of `blocked` or `deferred`, and an `author_gate_reason` of
`packet_final_answer_not_allowed` or `fixture_only_packet_author_deferred`.
For AG-96I2F, `author_activation_allowed` remains `false`,
`author_execution_deferred` remains `true`, and `final_text_included` remains
`false`.

## Closed Surfaces

AG-96I2F does not open:

- AuthorExecutor invocation;
- Author prompts or prose;
- user-visible product final-answer behavior;
- final_answer_outcome production;
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
- FinalAnswerPacket rebuilding;
- conversational Follow-up Turn Contract behavior;
- `core/pipeline_orchestrator.py` domain logic.

AG-96I2G or a later phase is required for either a fixture Author observation
or product-answer activation. Any later Author invocation must explicitly
license Author execution, prompt/prose behavior, citation rendering or
formatting behavior if changed, and product final-answer activation.

AG-96I2G is documented in
[AG96I2G_FOLLOWUP_SPINE_CLEANUP_AUDIT.md](AG96I2G_FOLLOWUP_SPINE_CLEANUP_AUDIT.md).
It audits and cleans the fixture-only AG-96I2A through AG-96I2F spine without
opening new Author, citation, provider/search, retrieval, fetch, model, or
product final-answer behavior.
