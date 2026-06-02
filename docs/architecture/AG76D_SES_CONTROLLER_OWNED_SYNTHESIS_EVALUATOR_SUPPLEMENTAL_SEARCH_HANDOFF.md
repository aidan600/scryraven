# AG-76D-SES / AG-76D-SES-R1 — Controller-Owned Synthesis-Evaluator Supplemental-Search Handoff

Status: AG-76D-SES-R1 implemented/readiness for review. AG-76D-SES introduced the passive Controller-owned handoff contract; AG-76D-SES-R1 wires the existing runtime path through that contract using already-computed legacy facts only.

## Scope

The handoff represents facts that the legacy synthesis-evaluator supplemental-search path already computed or exposed downstream:

- synthesis-evaluator run eligibility and run gate posture;
- completeness posture as `skipped`, `sufficient`, `insufficient`, or `parse_failed`;
- deficiency identity and deficiency text without rewriting evaluator output;
- supplemental query IDs, query text, source deficiency IDs, and source evaluator decision references;
- supplemental-search admission posture;
- supplemental provider role, provider list, search depth, and result count as protected already-computed legacy posture;
- supplemental evidence IDs, source IDs, URLs, count, and evidence refs;
- final evidence rebuild identity, including final bundle ID and final evidence/source IDs;
- Analyst re-run / re-analysis admission posture without performing re-analysis;
- Author note identity for `hedge_appropriately_where_data_is_missing` without altering Author prompt text or prose;
- compact AnswerContract, AnalystAuthorHandoff, and CitationSourceHandoff refs where available;
- JSON-safe Controller state and trace serialization under `synthesis_evaluator_supplemental_search_handoff`.

## Files

- `core/synthesis_evaluator_supplemental_search_handoff_contract.py`
- `core/synthesis_evaluator_supplemental_search_runtime_handoff.py`
- `core/pipeline_orchestrator.py`
- `tests/test_ag76d_ses_synthesis_evaluator_supplemental_search_handoff_contract.py`
- `tests/test_ag76d_ses_r1_synthesis_evaluator_supplemental_search_runtime_handoff.py`
- `docs/architecture/AG76D_SES_CONTROLLER_OWNED_SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF.md`

## Runtime wiring

AG-76D-SES-R1 adds `RuntimeSupplementalQueryFact`, `RuntimeSynthesisEvaluatorSupplementalSearchFacts`, and `RuntimeSynthesisEvaluatorSupplementalSearchFactCollector` for already-computed runtime posture. The collector owns defaulting and final fact construction so `core/pipeline_orchestrator.py` remains a tiny adapter touch: instantiate the collector, record already-computed branch facts, and attach one trace fragment near the existing handoff trace assembly. `build_runtime_synthesis_evaluator_supplemental_search_handoff(...)` converts those facts into `SynthesisEvaluatorSupplementalSearchHandoffState`, and `runtime_synthesis_evaluator_supplemental_search_trace_fragment(...)` returns the stable JSON-safe trace fragment.

`core/pipeline_orchestrator.py` records legacy facts as they occur and attaches the fragment under `synthesis_evaluator_supplemental_search_handoff`. The adapter does not authorize or perform evaluator calls, supplemental query generation, search, retrieval, final evidence rebuild, Analyst re-run, Author note creation, citation changes, persistence, cache behavior, or live validation.

## Explicit non-goals and closed behavior

AG-76D-SES-R1 is behavior-preserving runtime wiring only. It does not change:

- synthesis-evaluator behavior or evaluator output;
- prompt behavior;
- supplemental query generation;
- supplemental provider/search/depth selection;
- retrieval, ranking, filtering, or evidence selection;
- final evidence rebuild behavior;
- Analyst admission, execution, or re-run behavior;
- Author note wording, Author prompt inputs, or Author prose;
- citation/source-list behavior;
- Scrutineer/remediation behavior;
- source-class/currentness semantics;
- DB/session/`RunOutcome` shape;
- cache behavior;
- live validation posture.

The contract exposes these no-change guarantees through explicit `no_behavior_change_flags` and per-descriptor `changes_*_behavior: False` fields so future runtime consumers can distinguish represented legacy posture from authorized Controller authority.

## Trace shape

The Controller trace fragment is mechanically produced by `SynthesisEvaluatorSupplementalSearchHandoffState.to_trace_fragment()`:

```python
{
    "synthesis_evaluator_supplemental_search_handoff": state.to_controller_state()
}
```

The state is JSON-safe by construction. Runtime wiring sets `execution_envelope.runtime_wiring_active` to `True`, while `behavior_change_authorized` and `live_validation_performed` remain `False`.

## Validation

The AG-76D-SES fixture/static tests prove the passive contract shape. The AG-76D-SES-R1 runtime/adapter tests prove that:

1. evaluator skipped posture for strong retrieval / no supplemental check is represented;
2. sufficient posture with no supplemental search is represented;
3. insufficient posture with deficiency and supplemental queries is represented;
4. parse-failed posture is represented without changing legacy fallback behavior;
5. supplemental query IDs and source evaluator decision refs survive;
6. provider role/list/depth/result-count facts are protected legacy posture;
7. supplemental evidence identity survives;
8. final evidence rebuild identity survives;
9. Analyst re-run admission is represented without changing Analyst behavior;
10. Author note identity is represented without changing Author prompt text or prose;
11. AnswerContract, AnalystAuthorHandoff, and CitationSourceHandoff refs survive;
12. JSON-safe trace includes `synthesis_evaluator_supplemental_search_handoff`;
13. the runtime adapter does not import protected provider/orchestrator/persistence surfaces;
14. `core/pipeline_orchestrator.py` receives only a tiny adapter/trace touch.

## Next-phase posture

AG-76D-SCR-R1 and AG-76D-SES-R1 are complete/readiness for review. AG-78G remains live-gated. The recommended next phase is `AG-79D` (or another explicitly licensed passive handoff/runtime-consumption phase) rather than live validation or dogfood.
