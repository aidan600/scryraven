Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96I2H_FOLLOWUP_AUTHOR_OBSERVATION).

# AG-96I2H Follow-up Author Observation

## Status

AG-96I2H opens only explicit fixture Author output observation after the
AG-96I2F Author gate:

```text
RunKernel.followup_author_gate_state
+ RunKernel.final_answer_packet
+ RunKernel.final_answer_authority_projection
+ explicit fixture_author_output_payload
-> authorized fixture-only Author observation action
-> bounded adapter records sanitized output facts
-> RunKernel reducer derives packet-authority compliance
-> followup_author_observation_state/projection/history
```

This phase is fixture-only. It does not call `AuthorExecutor`, does not call a
model, does not generate or rewrite prose, does not render citations, and does
not activate product final-answer behavior. The explicit fixture payload is an
observation input, not authority.

## Runtime Records

The records live in `core.followup_author_observation_runtime` and are
schema-versioned as `followup_author_observation_ag96i2h_v1`:

- `FollowupAuthorObservationRequest`;
- `FollowupAuthorObservationResult`;
- `FollowupAuthorObservationObservation`;
- `FollowupAuthorObservationConsumptionRecord`.

They bind the AG-96I2A authorization consumption, AG-96I2B fixture execution,
AG-96I2C EvidenceLedger intake, AG-96I2D sufficiency recheck, AG-96I2E packet
preparation, AG-96I2F Author gate, packet ID, provider-job kind, component and
source-obligation links, requirement IDs, expected source classes, packet and
gate digests, fixture-only provenance, and closed Author/citation/product-answer
posture.

Raw final text is not retained. `report_text` or `final_text` may be supplied
only to compute `report_hash` and `report_length`. Canonical state records
`final_text_included: false`.

## RunKernel Consumption

RunKernel owns the new authorization and reducer seam:

```text
RunKernel.authorize_followup_author_observation(...)
-> execute_followup_author_observation_action(...)
-> RunKernel.reduce(...)
-> RunState.followup_author_observation_state/projection/history
```

Caller inputs are merged first and canonical binding fields are applied last.
The action binds canonical values from `followup_author_gate_state`,
`final_answer_packet`, and `final_answer_authority_projection`, including packet
ID, gate ID, all upstream follow-up IDs, modes, requirement IDs, expected source
classes, and digests.

The reducer rejects fixture-boundary violations such as `author_executor_invoked
= true`, `model_called = true`, `citation_formatter_invoked = true`,
`product_answer_behavior_changed = true`, `final_text_included = true`, or
`live_validation_not_run = false`. Packet-authority compliance failures are
accepted as canonical noncompliant fixture observations instead of crashing.

## Packet-Authority Compliance

Canonical compliance is derived by the RunKernel reducer from:

- FinalAnswerPacket mandatory caveats;
- FinalAnswerPacket prohibited upgrades;
- packet and gate citation-eligible source IDs;
- FinalAnswerPacket source-bound unknowns;
- FinalAnswerPacket missing and partial obligations;
- sanitized observed output facts.

Observation-supplied compliance claims, product-readiness claims, citation
eligibility claims, and activation flags are not trusted. A fixture output that
cites unauthorized source IDs, omits mandatory caveat acknowledgement, reports a
prohibited upgrade violation, or fails to acknowledge packet source-bound
unknowns is reduced as `packet_authority_compliance_status: noncompliant`.
Product answer behavior remains closed in compliant and noncompliant cases.

## Field Ownership Audit

| Canonical field group | Owner | Supplied or derived | Validation | Later authority risk | Regression mutation |
| --- | --- | --- | --- | --- | --- |
| Upstream IDs, packet ID, gate ID, modes, requirement IDs, expected classes, digests | `RunKernel.FollowupAuthorObservation` | Derived from `AuthorizedAction` and prior RunState | Binding guard compares observation to action and action to current gate/packet authority | Yes; future phases may consume IDs and digests | Caller override guard and gate-B-under-A binding guard |
| `observed_output_facts`, `report_hash`, `report_length`, `cited_source_ids` | `RunKernel.FollowupAuthorObservation` | Observation-supplied sanitized facts | Raw text and boundary fields rejected; raw text never retained | Yes, as observation facts only | Raw/boundary spoof guards |
| Compliance status fields | `RunKernel.FollowupAuthorObservation` | Derived from packet/gate authority plus sanitized facts | Reducer recomputes and overwrites spoofed claims | Yes; future phases may consume canonical compliance | Spoofed compliance is overwritten; citation/caveat/prohibited/unknown cases |
| Closed-surface flags | `RunKernel.FollowupAuthorObservation` | Derived closed posture | Action, adapter, and reducer require false/true no-live values | Yes; they prevent accidental activation | Boundary spoof tests mutate each dangerous flag |
| `final_text_included` and text hash/length fields | `RunKernel.FollowupAuthorObservation` | Hash/length are observation facts; inclusion flag is derived false | Raw text keys rejected in reduced observation | Yes; future phases may use hash-only evidence | Boundary spoof sets `final_text_included=true` |

## Compatibility State

AG-96I2H does not update `RunState.author_observation` or
`RunState.final_answer_outcome`. Those remain tied to real `AUTHOR_EXECUTE`
reduction and product Author output. Using only
`followup_author_observation_state/projection/history` avoids implying
user-visible final-answer behavior.

## Closed Surfaces

AG-96I2H does not open:

- `AuthorExecutor`;
- Author prompt selection or prompt mutation;
- Author prose generation;
- citation formatting or rendering;
- user-visible final answer display;
- live providers;
- search;
- retrieval;
- fetch/read;
- model calls;
- provider-job executors;
- provider routing, selection, depth, or query generation;
- retrieval ranking/filtering;
- SearchJudgment re-evaluation;
- SufficiencyJudgment rerun;
- FinalAnswerPacket rebuild;
- conversational Follow-up Turn Contract behavior;
- `core/pipeline_orchestrator.py` domain logic.

## Future Work

Future phases are still needed for real Author execution, prose quality
evaluation, citation rendering, product display, and any live validation. Those
surfaces require explicit phase scope and separate tests.

AG-96I2I follows this phase with a maintainability-only RunKernel audit and
mechanical follow-up reducer extraction:
[AG96I2I_FOLLOWUP_RUNKERNEL_MAINTAINABILITY_AUDIT.md](AG96I2I_FOLLOWUP_RUNKERNEL_MAINTAINABILITY_AUDIT.md).
