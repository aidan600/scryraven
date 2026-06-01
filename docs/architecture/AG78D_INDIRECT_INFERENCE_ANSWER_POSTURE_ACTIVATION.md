# AG-78D — Indirect Inference Answer Posture Activation

**Phase date:** 2026-06-01
**Phase type:** narrow protected-surface Controller / AnswerContract posture activation.

## Purpose

AG-78D activates bounded AnswerContract/controller posture metadata from the
already-visible AG-78C `indirect_inference_runtime_handoff` state. It is a small
metadata projection over AG-78B evaluator-authoritative `InferencePath` posture
and recommendation. It does not detect new inference opportunities or change the
answer text that users see.

The phase supports the ScryRaven posture that answers need not be
direct-citation-only, but inferred conclusions must not be presented as directly
sourced unless a source directly states the conclusion.

## Implementation

AG-78D adds `core/indirect_inference_answer_posture_activation.py` with:

- `IndirectInferenceAnswerPostureActivationInput`;
- `IndirectInferencePostureEffect`;
- `IndirectInferenceAnswerPostureActivation`;
- `build_indirect_inference_answer_posture_activation(...)`;
- `indirect_inference_answer_posture_activation_trace_fragment(...)`.

`core/answer_contract_runtime_handoff.py` attaches the optional activation only
when an AG-78C runtime handoff is already present. The trace/controller key is:

- `indirect_inference_answer_posture_activation`

The declared consumer remains:

- `answer_contract_runtime_handoff`

## Activated metadata

The activation output includes:

- schema/version and state key;
- consumer;
- per-path posture effects;
- a top-level posture summary;
- direct, inferred, speculative/unsupported, conflict-blocked,
  range/source-bound, and lower-tier non-satisfaction counts;
- `requires_inference_label=true` for inferred claims;
- `directly_sourced=false` for inferred conclusions;
- premise IDs, premise source IDs, bridge IDs, bridge types, and relationship
  source IDs;
- direct source IDs for directly sourced target claims;
- no-change behavior flags for final answer, Author, citations,
  provider/search/retrieval, and pipeline-orchestrator behavior;
- JSON-safe `to_controller_state()` and `to_trace_fragment()` helpers.

## Posture behavior

- Directly sourced paths remain `directly_sourced`, preserving direct source
  attribution.
- Balanced one-hop inferred paths become
  `inferred_from_sourced_premises` answer-posture effects with
  `directly_sourced=false` and `requires_inference_label=true`.
- Speculative/model-assumed and unsupported paths remain unsupported or
  speculative and cannot be upgraded by AG-78D.
- Constructor posture/recommendation override attempts remain impossible because
  AG-78D mirrors AG-78B evaluator-derived posture and recommendation.
- AG-77-derived `blocks` premise conflict impact activates
  `blocked_by_premise_conflict` posture metadata.
- Range-bound/source-bound numeric paths preserve unresolved scalar behavior by
  keeping `resolved_scalar=false` when range-bound.
- Lower-tier or non-satisfying premises do not satisfy stronger official,
  current, legal, canonical, or source-bound obligations.

## Protected surfaces

AG-78D does not change:

- final-answer prose;
- Author prompts, Author exposure, or Author evidence handoff;
- citation formatting, selection, ordering, or source ordering;
- provider/model/search/query behavior;
- retrieval ranking/filtering;
- source-class/currentness semantics;
- AG-77 conflict arbitration behavior;
- AG-78B evaluator semantics;
- Scrutineer/remediation behavior;
- Economist/follow-up behavior;
- DB/session/RunOutcome shape;
- cache behavior;
- live validation;
- actual inference opportunity detection;
- final inferred-answer presentation.

`core/pipeline_orchestrator.py` remains untouched.

## Tests

AG-78D adds `tests/test_ag78d_indirect_inference_answer_posture_activation.py`.
The tests cover direct, inferred, identity preservation, inference-label marker,
speculative non-upgrade, constructor override non-promotion, premise conflict
blocking, source-bound/range-bound unresolved numeric posture, lower-tier
non-satisfaction, empty/no-inference no-answer-impact behavior, immutability,
JSON-safe serialization, protected-import boundaries, pipeline-orchestrator
diff boundaries, and AnswerContract runtime handoff attachment.
