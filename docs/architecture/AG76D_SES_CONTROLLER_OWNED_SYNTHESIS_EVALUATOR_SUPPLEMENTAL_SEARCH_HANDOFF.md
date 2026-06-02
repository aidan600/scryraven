# AG-76D-SES — Controller-Owned Synthesis-Evaluator Supplemental-Search Handoff Contract

Status: implemented/readiness for review. AG-76D-SES adds a passive Controller-owned handoff contract for the synthesis-evaluator supplemental-search path. The phase is fixture/static-test only: it does not wire the contract into runtime, does not run live validation, and does not call providers, models, or search.

## Scope

The contract represents facts that the legacy synthesis-evaluator supplemental-search path already computed or exposed downstream:

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
- `tests/test_ag76d_ses_synthesis_evaluator_supplemental_search_handoff_contract.py`
- `docs/architecture/AG76D_SES_CONTROLLER_OWNED_SYNTHESIS_EVALUATOR_SUPPLEMENTAL_SEARCH_HANDOFF.md`

## Explicit non-goals and closed behavior

AG-76D-SES is representational only. It does not change:

- synthesis-evaluator behavior or evaluator output;
- prompt behavior;
- supplemental query generation;
- supplemental provider/search/depth selection;
- retrieval, ranking, filtering, or evidence selection;
- final evidence rebuild behavior;
- Analyst admission, execution, or re-run behavior;
- Author note wording, Author prompt inputs, or Author prose;
- citation/source-list behavior;
- DB/session/`RunOutcome` shape;
- cache behavior;
- `core/pipeline_orchestrator.py` behavior or runtime wiring;
- live validation posture.

The contract exposes these no-change guarantees through explicit `no_behavior_change_flags` and per-descriptor `changes_*_behavior: False` fields so future runtime wiring can distinguish represented legacy posture from authorized Controller authority.

## Trace shape

The Controller trace fragment is mechanically produced by `SynthesisEvaluatorSupplementalSearchHandoffState.to_trace_fragment()`:

```python
{
    "synthesis_evaluator_supplemental_search_handoff": state.to_controller_state()
}
```

The state is JSON-safe by construction and has no protected imports beyond `dataclasses`, `enum`, and `typing`.

## Validation

The fixture/static tests prove that:

1. skipped/sufficient/insufficient/parse-failed completeness postures serialize stably;
2. deficiency identity is preserved without changing evaluator output;
3. supplemental query identity and source evaluator decision are preserved;
4. provider/depth facts are represented as protected already-computed legacy posture;
5. supplemental evidence identity is represented;
6. final evidence rebuild identity is represented;
7. Analyst re-run admission is represented without re-running Analyst;
8. Author note identity is represented without changing Author prose;
9. AnswerContract / AnalystAuthorHandoff / CitationSourceHandoff refs survive;
10. Controller state and trace fragments are JSON-safe;
11. the contract does not import protected runtime/provider/prompt/cache/orchestrator surfaces;
12. `core/pipeline_orchestrator.py` remains unchanged.

## Next-phase posture

AG-76D-SCR-R1 is complete/readiness for review, and AG-76D-SES now covers the parked synthesis-evaluator supplemental-search handoff at passive contract depth. AG-78G remains live-gated. Any future phase that consumes this contract at runtime must be separately licensed and behavior-preserving unless Strategy explicitly authorizes a behavior change.
