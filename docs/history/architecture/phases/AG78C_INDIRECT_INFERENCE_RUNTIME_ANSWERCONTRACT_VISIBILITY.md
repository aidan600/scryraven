Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG78C_INDIRECT_INFERENCE_RUNTIME_ANSWERCONTRACT_VISIBILITY).

# AG-78C — Indirect Inference Runtime / AnswerContract Visibility

**Phase date:** 2026-06-01
**Phase type:** protected-surface runtime / AnswerContract visibility integration, no final-answer behavior change.

## Purpose

AG-78C makes AG-78B indirect inference posture visible to runtime, Controller,
AnswerContract, and trace consumers. It serializes already-constructed AG-78B
`InferencePath` objects into a JSON-safe handoff. It does **not** perform
inference, detect inference opportunities, change final-answer prose, alter
Author exposure, change citations, affect retrieval, call providers, or persist
new DB/session/RunOutcome state.

## Relationship to AG-78A, AG-78B, and AG-78B-R1

- **AG-78A** defines the indirect evidence / inference posture design: ScryRaven
  may infer from sourced premises when the inference path is legitimate,
  mode-appropriate, and honestly labeled.
- **AG-78B** adds the inert Controller-visible inference contract in
  `core/indirect_inference_contract.py`.
- **AG-78B-R1** makes the evaluator-derived `InferencePath.posture` and
  `InferencePath.recommendation` authoritative. Constructor-supplied posture or
  recommendation values cannot upgrade invalid, blocked, speculative,
  unsupported, or mode-disallowed paths.
- **AG-78C** consumes those AG-78B objects as immutable inputs and exposes their
  already-evaluated posture and recommendation to runtime / AnswerContract
  state.

## Visibility-only stance

AG-78C is a visibility handoff. The runtime helper reports what AG-78B already
knows; it does not determine whether an answer should state an inferred
conclusion. The protected-surface flags remain false, and `no_answer_impact` is
true in the handoff state.

## Runtime handoff schema summary

The handoff schema version is
`AG78C.indirect_inference_runtime_answercontract_visibility.v1`.

Each path entry includes:

- target claim ID and text;
- target claim posture and evaluator-derived path posture;
- direct / inferred / speculative / unsupported marker;
- inference mode and depth;
- evaluator-derived path recommendation;
- premise IDs and premise source IDs;
- bridge IDs, bridge types, and relationship source IDs;
- AG-77 premise conflict impacts;
- source-bound numeric marker and resolved-scalar visibility;
- lower-tier non-satisfaction marker;
- evaluator-authoritative posture/recommendation marker;
- protected-surface no-change flags.

## Trace key / controller state key

AG-78C uses a stable runtime handoff key:

- `indirect_inference_runtime_handoff`

The state also records the AG-78B source key:

- `indirect_inference_contract`

The declared consumer is `answer_contract_runtime_handoff`.

## Directly sourced visibility behavior

Directly sourced AG-78B target claims remain directly sourced in AG-78C
visibility. The handoff preserves `target_claim_id`, `target_claim_text`,
`target_claim_posture=directly_sourced`, `path_posture=directly_sourced`,
`support_marker=direct`, and `directly_sourced_target=true`.

## Inferred-from-sourced-premises visibility behavior

Balanced one-hop inferred paths preserve the evaluator-derived
`inferred_from_sourced_premises` posture, `may_state` recommendation, inference
mode, premise IDs, premise source IDs, bridge IDs, bridge types, and
relationship source IDs. AG-78C does not expose the posture to Author or final
answer generation.

## Speculative / unsupported visibility behavior

Speculative or unsupported AG-78B paths remain speculative or unsupported after
handoff serialization. AG-78C cannot upgrade a model-assumed/speculative bridge
or an unsupported path into supported inferred posture.

## AG-77 premise conflict impact visibility

Premise conflict impacts from AG-78B premises are serialized under
`premise_conflict_impacts` and `ag77_premise_conflict_impact`. Blocking,
weakening, range-bounding, background-only, and non-satisfying impacts are
reported without changing AG-77 arbitration behavior.

## Source-bound numeric range / unresolved visibility

AG-78C reports source-bound numeric state with `source_bound_numeric_present`,
`source_bound_numeric_marker`, and `resolved_scalar`. Range-bound inference is
serialized as `range_bound` and does not become a resolved scalar.

## Lower-tier non-satisfaction visibility

Premises marked `NON_SATISFYING_FOR_OBLIGATION` or
`satisfies_required_source_obligation=false` produce
`lower_tier_non_satisfaction=true`. Such paths remain unsupported and do not
become inferred support through the runtime handoff.

## Evaluator-authoritative posture guarantee

AG-78C preserves AG-78B-R1 semantics. It reads `InferencePath.posture` and
`InferencePath.recommendation` after AG-78B evaluation and marks
`evaluator_authoritative_posture_recommendation=true`. It does not re-open
constructor override promotion.

## Immutability guarantee

AG-78B `InferencePath` objects are treated as immutable inputs. The AG-78C
helper builds JSON-safe dictionaries from path state and does not mutate the
input path, premises, bridges, target claim, notes, or protected-surface flags.

## Pipeline-orchestrator boundary

`core/pipeline_orchestrator.py` remains outside AG-78C. No inference detection,
path construction, prompt wiring, Author exposure, citation behavior, provider
behavior, retrieval behavior, persistence, cache behavior, or broad orchestrator
integration is added.

## Tests added

AG-78C adds `tests/test_ag78c_indirect_inference_runtime_handoff.py`, covering:

direct visibility, Balanced one-hop inferred visibility, speculative / unsupported
non-upgrade behavior, evaluator authority, constructor override non-promotion,
premise and bridge source serialization, AG-77 conflict impact serialization,
source-bound numeric range visibility, lower-tier non-satisfaction visibility,
empty no-inference/no-answer-impact state, JSON-safe serialization, AG-78B input
immutability, protected-import guarding, and pipeline-orchestrator diff guarding.

## Protected surfaces kept closed

AG-78C keeps final-answer prose, Author prompts/exposure/evidence handoff,
citation formatting/selection/ordering, provider/model/search/query behavior,
retrieval ranking/filtering, source-class/currentness semantics, AG-77 conflict
arbitration, Scrutineer/remediation, Economist/follow-up, DB/session/RunOutcome
shape, cache behavior, live validation, and actual inference execution closed.

## Stop conditions

Future work should stop rather than extend AG-78C if it requires final-answer
prose changes, Author exposure changes, citation changes, provider/search/query
changes, retrieval changes, DB/session/RunOutcome changes, cache changes,
Scrutineer/remediation changes, Economist/follow-up changes, broad
`pipeline_orchestrator.py` integration, broader inference detection, source
class/currentness semantic changes, AG-77 arbitration changes, AG-78B evaluator
changes, or product decisions about final prose labeling of inferred answers.

## Recommended next phase

Recommended next phase: **AG-78D — Indirect Inference Runtime Behavior
Activation / Answer Posture Effects**.

Alternatives: **AG-78C-R1** if runtime visibility reveals a contract issue, or
**AG-77E** if Strategy wants conflict presentation before inference behavior
activation. Cache implementation is not recommended as the next phase.
