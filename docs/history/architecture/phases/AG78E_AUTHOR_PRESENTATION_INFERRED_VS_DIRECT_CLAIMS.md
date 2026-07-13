Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG78E_AUTHOR_PRESENTATION_INFERRED_VS_DIRECT_CLAIMS).

# AG-78E — Author / Presentation for Inferred-vs-Direct Claims

**Phase date:** 2026-06-02
**Phase type:** narrow Author / final-answer presentation activation.

## Purpose

AG-78E makes Author/final-answer presentation context distinguish directly
sourced claims from conclusions inferred from sourced premises. ScryRaven is not
direct-citation-only: it may state legitimate, mode-appropriate inferences from
sourced premises, but those conclusions must be honestly labeled and must not be
presented as directly source-stated unless a source directly states the
conclusion.

## Relationship to AG-78A/B/B-R1/C/D

- AG-78A supplied the architecture design for direct evidence, sourced-premise
  inference paths, caveats, range-bound numeric posture, and AG-77 conflict
  interaction.
- AG-78B supplied the inert `InferencePath`/posture contract.
- AG-78B-R1 made evaluator-derived posture/recommendation authoritative.
- AG-78C made indirect-inference posture visible to runtime / AnswerContract
  state without changing final-answer behavior.
- AG-78D activated bounded AnswerContract posture metadata from the AG-78C
  handoff.
- AG-78E consumes only the already-activated AG-78D posture effects and projects
  them into Author/final-answer presentation labels.

AG-78E does not reconstruct facts, re-evaluate paths, broaden inference
detection, or change AG-78B/AG-78D semantics.

## Licensed presentation changes

AG-78E adds `core/indirect_inference_author_presentation_handoff.py` and exposes
an optional `indirect_inference_author_presentation_handoff` trace fragment from
`core/answer_contract_runtime_handoff.py` when AG-78D activation is already
present. The handoff is additive and JSON-safe.

Licensed labels are:

- `directly_sourced`;
- `inferred_from_sourced_premises`;
- `speculative_or_unsupported`;
- `blocked_by_premise_conflict`;
- `range_bound_or_source_bound`.

Each claim carries `inference_label_required`, `directly_sourced`, premise IDs,
premise source IDs, bridge IDs, bridge types, bridge relationship source IDs,
resolved-scalar posture, lower-tier non-satisfaction posture, and source
attribution boundary text.

## Directly sourced presentation behavior

A directly sourced target claim remains labeled `directly_sourced`. Its direct
source IDs are exposed as `conclusion_direct_source_ids`, and its
`source_attribution_mode` is `direct_source_statement`.

## Inferred-from-sourced-premises presentation behavior

An inferred conclusion is labeled `inferred_from_sourced_premises` with the human
label `inferred from sourced premises`. It carries
`inference_label_required=true` and `directly_sourced=false`. Premise and bridge
source IDs remain visible for attribution, but they are explicitly not direct
source IDs for the conclusion.

## Speculative/unsupported presentation behavior

Unsupported, speculative, and declined paths are labeled
`speculative_or_unsupported`. They do not set `inference_label_required`, and
AG-78E does not upgrade them into supported inference.

## Blocked-by-premise-conflict presentation behavior

Paths blocked by AG-77-derived premise conflict posture are labeled
`blocked_by_premise_conflict`. They are not presented as supported inferred
conclusions.

## Range-bound/source-bound numeric presentation behavior

Range-bound or source-bound numeric paths are labeled
`range_bound_or_source_bound`. They preserve unresolved scalar posture by keeping
`resolved_scalar=false` for presentation when the numeric result remains
range/source-bound.

## Lower-tier non-satisfaction presentation behavior

Lower-tier or otherwise non-satisfying premise posture survives into Author
presentation context through `lower_tier_non_satisfaction=true` and
`stronger_obligation_satisfied=false`. AG-78E does not allow lower-tier evidence
to satisfy stronger official/current/legal/canonical/source-bound obligations.

## Citation/source-attribution boundary

Premise and bridge sources support the premises and bridge relationships. They
do not mean the inferred conclusion was directly source-stated unless the claim
is labeled `directly_sourced`. For inferred conclusions,
`conclusion_direct_source_ids` remains empty and
`premise_bridge_sources_support_direct_conclusion=false`.

This is a citation-laundering guard only. It does not change citation selection,
source ordering, formatting, retrieval ranking, or source-class/currentness
semantics.

## Tests added

AG-78E adds `tests/test_ag78e_indirect_inference_author_presentation.py`. The
tests cover direct claim labeling, inferred claim labeling, no direct-source
laundering, premise/bridge source visibility, speculative/unsupported posture,
blocked-by-conflict posture, range/source-bound numeric posture, lower-tier
non-satisfaction, AnswerContract runtime attachment, JSON-safe behavior flags,
protected-import boundaries, and the pipeline-orchestrator diff boundary.

## Protected surfaces kept closed

AG-78E does not change:

- provider/model/search/query behavior;
- retrieval ranking/filtering;
- source-class/currentness semantics;
- AG-78B evaluator semantics;
- AG-78D posture activation semantics;
- AG-77 conflict arbitration behavior;
- citation selection, source ordering, or broad citation formatting;
- DB/session/RunOutcome shape;
- cache behavior;
- Scrutineer/remediation behavior;
- Economist/follow-up behavior;
- broad pipeline orchestration;
- live validation;
- inference-opportunity detection;
- raw prompts or raw provider payload handling.

`core/pipeline_orchestrator.py` remains untouched.

## Stop conditions

Stop rather than expanding AG-78E if any of the following become necessary:

- provider/search/query/retrieval behavior changes;
- broader inference detection;
- AG-78B evaluator rule changes;
- AG-78D activation semantic changes;
- AG-77 conflict arbitration changes;
- citation ordering/selection redesign;
- live provider/model/search calls;
- broad `core/pipeline_orchestrator.py` changes;
- product decisions beyond direct-vs-inferred-vs-unsupported/range/conflict
  presentation labeling.

## Recommended next phase

Recommended next phase: **AG-78F — Indirect Inference Presentation Burn-Down /
Dogfood Prep**. AG-78E intentionally stays narrow; AG-78F can review presentation
copy, trace ergonomics, and dogfood readiness before any live validation is
considered.
