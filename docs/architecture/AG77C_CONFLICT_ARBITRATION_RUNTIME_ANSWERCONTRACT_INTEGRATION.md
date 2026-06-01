# AG-77C — Conflict Arbitration Runtime / AnswerContract Integration

Date: 2026-06-01

## Phase type

Protected-surface integration, with no final-answer behavior change.

## Purpose

AG-77C makes the AG-77B Controller-owned source-conflict arbitration posture visible to Controller / AnswerContract runtime state and trace consumers. It consumes AG-77A source-conflict representations and AG-77B arbitration state without changing final answer prose, Author inputs, citation behavior, prompt text, provider/search/query behavior, retrieval behavior, or conflict-resolution behavior.

## No-prose-change stance

The integration is visibility-only. The runtime handoff records `no_prose_change=True`, `final_answer_behavior_changed=False`, `author_behavior_changed=False`, `author_exposure_changed=False`, `citation_behavior_changed=False`, `prompt_behavior_changed=False`, `provider_search_query_behavior_changed=False`, `retrieval_behavior_changed=False`, and `numeric_output_behavior_changed=False`.

Evidence preservation is not Author exposure: the arbitration posture is trace/controller state for Controller / AnswerContract runtime visibility, not a final-answer instruction.

## Inputs consumed

### AG-77A representation

`core.source_conflict_model.SourceConflictRepresentation` may be supplied to the AG-77C helper. If present and no arbitration state is supplied, the helper passes the immutable representation to AG-77B arbitration. AG-77C does not broaden conflict detection or construct new conflict facts from evidence.

### AG-77B arbitration state

`core.source_conflict_arbitration.SourceConflictArbitrationState` may be supplied directly. When supplied, AG-77C serializes its existing controller state and does not recompute arbitration.

## Runtime / AnswerContract-visible handoff schema

The additive handoff lives in `core/source_conflict_arbitration_runtime_handoff.py` and emits a trace fragment under the stable key `source_conflict_arbitration` with schema version `AG77C.conflict_arbitration_runtime_answercontract_handoff.v1`.

Top-level fields include:

- `schema_version`
- `trace_key`
- `consumer`
- `author_exposed`
- `visibility_only`
- `source_conflict_representation_available`
- `input_representation_schema_version`
- `arbitration_schema_version`
- `arbitration`
- `top_level_disposition`
- `top_level_answer_posture`
- `unresolved_blocking_count`
- `unresolved_nonblocking_count`
- `preserved_source_ids`
- `ledger_compatible`
- no-change behavior flags

`RuntimeAnswerContractFacts` has optional `source_conflict_representation` and `source_conflict_arbitration_state` fields. When either is supplied, `build_runtime_answer_contract_handoff(...)` attaches the AG-77C trace fragment. When neither is supplied, existing AnswerContract runtime handoff output is unchanged.

## No-conflict / no-answer-impact default

When no AG-77A representation is available, AG-77C returns an explicit no-conflict/no-answer-impact packet instead of forcing conflict construction. The default exposes:

- `top_level_disposition=no_conflict`
- `top_level_answer_posture=no_answer_impact`
- zero unresolved counts
- empty preserved source IDs
- `no_conflict_default=True`
- all behavior-change flags set to `False`

Empty AG-77A representations similarly serialize to no-conflict/no-answer-impact posture through AG-77B state.

## Unresolved official/current posture visibility

For equal official/current central conflicts, AG-77B may expose `unresolved_blocking` and `insufficient_for_authoritative_answer`. AG-77C carries those values into Controller / AnswerContract-visible state and trace only. It does not block final answers, alter Author behavior, modify prompt assembly, change citations, or change provider/search/retrieval behavior.

## Source-bound numeric unresolved posture visibility

For source-bound numeric conflicts, AG-77B may expose `source_bound_value_unresolved`. AG-77C serializes that posture and records `numeric_output_behavior_changed=False`. The numeric posture is not active in final-answer generation in AG-77C.

## Lower-tier non-satisfaction visibility

For official/current obligations where secondary or lower-tier evidence is present, AG-77B can mark lower-tier evidence as non-satisfying while preserving it as background/context. AG-77C preserves the `non_satisfying_claim_ids`, `background_only_claim_ids`, and `lower_tier_cannot_satisfy_stronger_obligation` flags in runtime-visible arbitration state. This makes weaker evidence visible without allowing it to satisfy stronger official/current/legal/canonical/source-bound obligations.

## Trace/controller serialization

AG-77C emits JSON-safe controller state and trace fragments. Serialization is limited to dict/list/scalar values copied from AG-77B controller state plus AG-77C visibility metadata. The stable trace key remains `source_conflict_arbitration` so downstream Controller / AnswerContract trace consumers can locate the posture without Author exposure.

## Immutability guarantees

AG-77C treats AG-77A and AG-77B objects as immutable inputs:

- it does not mutate `SourceConflictRepresentation`;
- it does not mutate `SourceConflictArbitrationState`;
- it deep-copies serialized controller state before adding AG-77C metadata.

## Pipeline-orchestrator boundary

`core/pipeline_orchestrator.py` is intentionally untouched. AG-77C uses a small helper plus optional AnswerContract runtime handoff fields instead of adding domain logic to orchestration. There is no new branching on arbitration disposition, answer posture, source classes, citations, prompts, providers, search, retrieval, Scrutineer, Economist, follow-up, DB/session, RunOutcome, cache, or AG-78 inference.

## Tests added

`tests/test_ag77c_conflict_arbitration_runtime_handoff.py` covers:

1. runtime / AnswerContract-visible state carrying arbitration posture;
2. AnswerContract runtime trace attachment when optional AG-77C facts are supplied;
3. no-conflict/no-answer-impact defaults;
4. central unresolved official/current visibility only;
5. source-bound numeric unresolved visibility only;
6. official/current vs secondary lower-tier non-satisfaction visibility;
7. JSON-safe trace/controller serialization;
8. AG-77A immutability;
9. AG-77B immutability;
10. static protected-import guard;
11. pipeline-orchestrator untouched guard.

## Protected surfaces kept closed

AG-77C does not change:

- final-answer prose behavior;
- Author behavior or Author exposure;
- citation formatting, citation selection, or source ordering;
- prompt text or prompt semantics;
- provider/model/search/query behavior;
- retrieval ranking/filtering;
- source-class recovery behavior;
- weak-corpus recovery behavior;
- Scrutineer/remediation behavior;
- Economist/follow-up behavior;
- DB/session/RunOutcome shape;
- cache behavior;
- AG-78 indirect inference;
- conflict detection semantics;
- source classification/currentness semantics.

## Stop conditions

Work should stop and move to a later behavior phase if making arbitration posture visible requires any of the following:

- blocking authoritative answers;
- changing final-answer prose;
- exposing conflict posture to Author;
- changing citation behavior;
- changing prompt semantics;
- changing provider/search/query or retrieval behavior;
- changing Scrutineer/remediation, Economist/follow-up, DB/session/RunOutcome, or cache behavior;
- implementing AG-78 indirect inference;
- adding new conflict detection or source classification semantics.

## Expected next phase options

- **AG-77D — Conflict Arbitration Runtime Behavior Activation / Answer Posture Effects.** Recommended if the project wants the now-visible arbitration posture to influence answer posture under a narrow behavior license.
- **AG-78A — Controller-Owned Indirect Evidence / Inference Posture Design.** Use if strategy pivots to inference design before activating conflict-arbitration behavior.
- **AG-76D-SCR.** Use if Scrutineer/remediation must consume arbitration posture.
- **AG-76D-AD.** Use if adapter debt blocks safe integration.
