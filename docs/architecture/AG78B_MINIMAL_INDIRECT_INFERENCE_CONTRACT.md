# AG-78B — Minimal Indirect Inference Contract with Fixture Tests

Date: 2026-06-01

Phase type: minimal inert Controller-visible contract implementation with fixture/static tests.

## Purpose

AG-78B adds the first pure contract for representing indirect inference without changing runtime or final-answer behavior. The contract is intentionally limited to Controller-visible state and trace fragments that can say: a target claim was directly sourced, inferred from sourced premises through an explicit bridge, caveated/range-bound by premise quality, blocked by AG-77 premise conflict posture, unsupported, speculative, or declined.

This phase does not execute inference. It does not alter Author behavior, prompt text, final-answer prose, citation formatting/selection/ordering, provider/model/search/query behavior, retrieval behavior, source-class/currentness semantics, conflict arbitration behavior, Scrutineer/remediation, Economist/follow-up behavior, DB/session/RunOutcome shape, cache behavior, or `core/pipeline_orchestrator.py`.

## Relationship to AG-78A

AG-78A defined the architecture posture for indirect evidence and inference. AG-78B implements the minimal inert contract shape implied by that design: target claims, sourced premises, explicit inference bridges, inference paths, source attribution, mode policy, bridge taxonomy, premise-conflict impact, and JSON-safe Controller/trace serialization.

AG-78B is narrower than the full AG-78A design. It proves a Balanced one-hop representation contract and a static protected-surface boundary; runtime visibility and AnswerContract integration remain for AG-78C.

## Direct vs inferred vs speculative distinction

The contract distinguishes three key evidence families:

1. `directly_sourced`: the source attribution belongs to the target claim because a source states the target claim itself.
2. `inferred_from_sourced_premises`: the target claim is not directly sourced, but sourced premises and an explicit valid bridge support a one-hop path to the target.
3. `speculative` / `unsupported`: a bridge is model-assumed, speculative, invalid, missing, disallowed by mode, or dependent on premises that cannot satisfy the relevant obligation.

An inferred claim is never marked as directly sourced unless a source attribution is attached to the target claim and the target posture is `directly_sourced`.

## Contract schema summary

The implementation lives in `core/indirect_inference_contract.py` and exposes:

- `InferenceSourceAttribution`: source identity, class/tier, title/URL/publisher, dates/effective periods, jurisdiction, and scope.
- `TargetClaim`: target claim identity, text, posture, direct-source marker, source attribution, value/unit, jurisdiction/scope/date, and scalar-resolution marker.
- `SourcedPremise`: premise identity, source identity, value/unit, dates/effective periods, jurisdiction/scope, AG-77-derived conflict impact, source-bound numeric marker, and source-obligation satisfaction marker.
- `InferenceBridge`: bridge identity, bridge type, bridge strength, allowed modes, relationship source attribution, assumption labels, and validity marker.
- `InferencePath`: target, premises, bridges, mode, depth, evaluated posture/recommendation, Controller/trace visibility, notes, and protected-surface flags.

The schema version is `AG78B.minimal_indirect_inference_contract.v1`. The trace/controller key is `indirect_inference_contract`.

## Bridge taxonomy

AG-78B represents these bridge types:

- `mathematical`: arithmetic, formula, conversion, or other exact numeric relationship when units/scope are compatible.
- `definitional`: application of a sourced definition to sourced facts.
- `legal_statutory`: application of official/current legal or statutory premises, represented conservatively.
- `domain_standard`: application of a sourced or canonical domain convention.
- `source_stated_relationship`: a source states the relationship/rule and another premise supplies the input.
- `model_assumed_speculative`: the model supplies an unsourced relationship, causal link, typicality assumption, or missing rule; this cannot support a sourced-premise inference posture.

## Mode policy summary

- `fast`: mostly direct evidence only. Non-trivial multi-premise inference is declined/unsupported.
- `balanced`: controlled one-hop inference only. Multi-hop inference is declined/unsupported.
- `deep`: can represent multi-hop posture and assumptions, but AG-78B still does not execute final-answer behavior.

## Balanced one-hop inference scope

Balanced mode may represent one-hop mathematical, definitional, source-stated relationship, simple sourced/canonical domain-standard, and conservative legal/statutory bridge paths when required premises are sourced, compatible, and not blocked by conflict posture. The target is labeled `inferred_from_sourced_premises` only when the bridge is valid and non-speculative and all required premises remain usable.

## Deep multi-hop representation boundary

Deep mode can represent multi-hop paths by carrying multiple bridges and `depth > 1`. This is only a posture/trace representation in AG-78B. It does not cause runtime inference execution, final-answer prose, Author exposure, citation changes, provider calls, retrieval changes, or orchestrator integration.

## Fast-mode rejection boundary

Fast mode rejects non-trivial multi-premise inference. A Fast path with multiple required premises or depth greater than one is evaluated as declined/unsupported rather than upgraded to an inferred answer.

## AG-77 premise conflict interaction

`PremiseConflictImpact` carries the AG-77-derived impact of conflict posture on premise usability:

- `none`: no conflict impact represented.
- `weakens`: the path can only be caveated.
- `range_bounds`: the path can only be range-bound.
- `blocks`: the path is blocked/declined.
- `background_only`: the path can only be caveated/backgrounded.
- `non_satisfying_for_obligation`: the premise cannot satisfy the requested official/current/legal/canonical obligation.

AG-78B does not change AG-77 conflict arbitration behavior; it only represents how an already-known conflict impact affects the inference path.

## Source-bound numeric premise handling

Source-bound numeric conflicts are not collapsed into a resolved scalar. When required numeric premises are range-bound by unresolved source conflict, `InferencePath` evaluates to `range_bound_inference` with `range_bound` recommendation and reports `resolved_scalar` as false in Controller state.

## Source hierarchy / lower-tier non-satisfaction handling

A lower-tier premise cannot satisfy an official/current/legal/canonical obligation merely because it is available. Such premises are represented with `non_satisfying_for_obligation` or `satisfies_required_source_obligation=False`, producing unsupported/caveated posture instead of an authoritative inferred answer.

## Serialization and trace keys

`InferencePath.to_controller_state()` returns a JSON-safe dictionary with:

- schema/version and state key;
- target claim, premise, bridge, source, mode, depth, posture, and recommendation fields;
- preserved target claim IDs, premise IDs, bridge IDs, premise source IDs, and bridge relationship source IDs;
- direct/inferred markers;
- resolved-scalar marker;
- protected-surface flags.

`InferencePath.to_trace_fragment()` returns a JSON-safe trace fragment under `indirect_inference_contract` with the same identities and protected-surface summary.

## Tests added

`tests/test_ag78b_indirect_inference_contract.py` covers:

1. direct target claim vs inferred target claim;
2. Balanced one-hop mathematical inference;
3. Balanced one-hop definitional inference;
4. source-stated relationship source preservation;
5. speculative/model-assumed bridge rejection;
6. Fast rejection of non-trivial multi-premise inference;
7. Balanced rejection of multi-hop inference;
8. Deep multi-hop representation with protected final-answer flags;
9. AG-77 blocking premise-conflict impact;
10. weak/background conflict caveating;
11. source-bound numeric range-bound/unresolved scalar posture;
12. lower-tier non-satisfaction;
13. JSON-safe Controller/trace serialization;
14. protected-surface flags;
15. static guard that the contract does not import or rewrite `core/pipeline_orchestrator.py`.

## Protected surfaces kept closed

AG-78B keeps these surfaces closed and marks them false in the contract flags: final-answer behavior, Author behavior/exposure, citation behavior, provider/search/query/retrieval behavior, DB/session/RunOutcome behavior, cache behavior, Scrutineer behavior, Economist/follow-up behavior, orchestrator behavior, runtime inference execution, and live validation behavior.

## Stop conditions

This phase must stop rather than proceed if implementation requires runtime final-answer behavior, Author prompts/exposure, citation behavior, provider/search/query behavior, retrieval behavior, source-class/currentness semantics, AG-77 conflict arbitration behavior, Scrutineer/remediation, Economist/follow-up behavior, DB/session/RunOutcome shape, cache implementation, `core/pipeline_orchestrator.py` changes, live provider/model/search validation, AG-78C runtime integration, or final prose product decisions.

No stop condition was required for the minimal inert contract.

## Recommended next phase

Recommended next phase: AG-78C — Runtime / AnswerContract Visibility for Indirect Inference.

AG-78C should make this inert contract visible to runtime/AnswerContract state without changing final-answer behavior, Author prompts/exposure, citation behavior, provider/search/query/retrieval behavior, or live validation posture.
