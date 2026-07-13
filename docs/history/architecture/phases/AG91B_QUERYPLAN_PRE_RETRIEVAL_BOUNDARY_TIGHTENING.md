Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG91B_QUERYPLAN_PRE_RETRIEVAL_BOUNDARY_TIGHTENING).

# AG-91B QueryPlan Pre-Retrieval Boundary Tightening

Status: implementation phase; behavior-preserving authority-boundary tightening; no live validation

Branch: `ag-91b-queryplan-pre-retrieval-boundary-tightening`
Base: `main`

## Purpose

AG-91B implements the first AG-91A recommendation: pre-retrieval query candidates
from router/recon/researcher/recency/local finalization must be consumed from
`QueryPlan`-authorized output rather than from a parallel orchestrator-local
query authority path.

This phase does not change prompt text, provider selection, search depth,
retrieval execution, ranking/filtering, final evidence, citation formatting,
Author behavior, persistence, cache behavior, or any live provider/model/search
or embedding call shape.

## Inspected pre-retrieval query path

The inspected path in `core/pipeline_orchestrator.py` is:

1. Router output and retry normalization build the router query-preparation
   runtime posture.
2. Brave recon may seed replacement query candidates and a canonical subject.
3. If recon does not seed queries, the researcher model produces initial query
   candidates or falls back to the core topic.
4. Query candidates are finalized through `QueryPlanRuntimeAdapter.finalize(...)`,
   which delegates to `core.query_plan.authorize_retrieval_queries(...)`.
5. The initial max-query slice remains unchanged.
6. Recency merge, when applicable, is authorized through
   `QueryPlanRuntimeAdapter.merge_recency(...)`.
7. The consumed pre-retrieval query list is finalized again through
   `QueryPlanRuntimeAdapter.finalize(...)` with the existing max-query cap and no
   official-bias reinsertion.
8. The retrieval loop admits the exact `current_queries` through
   `QueryPlanRuntimeAdapter.admit_execution_queries(...)`, then replaces
   `current_queries` with the QueryPlan projection for that iteration before
   dispatch.
9. `queries_by_iteration` is read from `QueryPlanRuntimeAdapter.queries_by_iteration()`.

## Old authority path demoted/deleted/bypassed

The orchestrator-local `_finalize_retrieval_queries(...)` facade was deleted. It
had no independent logic, but its name and local placement made the orchestrator
look like it retained a parallel pre-retrieval finalization authority. The
orchestrator now calls the QueryPlan runtime adapter directly for initial
finalization and post-recency/max-cap finalization.

The retrieval loop now assigns `current_queries` from
`QueryPlanRuntimeAdapter.admit_execution_queries(...)`. That return value is the
QueryPlan-authorized projection for the current iteration, so dispatch consumes
the same list that QueryPlan records instead of relying on a local mirror after
recording.

## Consumed QueryPlan output path

The consumed path is now:

```text
router/recon/researcher candidates
  -> QueryPlanRuntimeAdapter.finalize(...)
  -> current max-query slice
  -> QueryPlanRuntimeAdapter.merge_recency(...) when applicable
  -> QueryPlanRuntimeAdapter.finalize(..., max_len=max_queries, include_official_bias=False)
  -> QueryPlanRuntimeAdapter.admit_execution_queries(...)
  -> QueryPlan.authorized_queries_by_iteration[iteration]
  -> retrieval dispatch current_queries
```

`queries_by_iteration` remains a QueryPlan projection and is not reconstructed
from a separate orchestrator-local list.

## Behavior-preservation proof

Focused offline tests cover exact query text/order parity for:

- initial researcher candidates versus legacy `finalize_retrieval_queries(...)`;
- recon-seeded candidates versus legacy `finalize_retrieval_queries(...)`;
- recency merge text/order after admission;
- official/current/canonical bias insertion order and custody separation;
- max-query cap consumed list and over-budget rejected records;
- retrieval-loop consumed `current_queries` matching QueryPlan records;
- `queries_by_iteration` being derived from QueryPlan projection rather than a
  local mirror;
- static guarding that `QueryPlan`/runtime adapter do not import or call closed
  provider/search/depth/prompt/model/citation/final-evidence surfaces.

Existing AG-89C QueryPlan tests continue to prove parity with the legacy
`core.retrieval_quality.finalize_retrieval_queries(...)` behavior.

## Tests run

Offline checks run for this phase:

- `python -m pytest tests/test_query_plan_ag89c.py -q`
- `python -m pytest tests/test_query_plan_ag89c.py tests/test_domain_query_anchoring.py tests/test_weak_corpus_recovery.py tests/test_retrieval_stop_shadow.py -q`
- `python -m pytest tests/test_ag77a_source_conflict_representation_model.py::test_lane_distinction_static_guard_and_pipeline_orchestrator_unchanged tests/test_ag77b_source_conflict_arbitration.py::test_pipeline_orchestrator_is_not_rewritten tests/test_ag77c_conflict_arbitration_runtime_handoff.py::test_pipeline_orchestrator_adapter_guard_untouched tests/test_ag77d_conflict_arbitration_answer_posture_activation.py::test_pipeline_orchestrator_boundary_only_has_unrelated_scrutineer_handoff_touch tests/test_ag78b_indirect_inference_contract.py::test_static_guard_contract_does_not_import_or_rewrite_pipeline_orchestrator tests/test_ag78c_indirect_inference_runtime_handoff.py::test_pipeline_orchestrator_remains_untouched_in_diff tests/test_ag78d_indirect_inference_answer_posture_activation.py::test_pipeline_orchestrator_remains_untouched_in_diff tests/test_ag78e_indirect_inference_author_presentation.py::test_pipeline_orchestrator_only_has_unrelated_scrutineer_handoff_touch tests/test_ag79b_provider_search_authority_boundary.py::test_pipeline_orchestrator_boundary_guard_untouched tests/test_document_review_ag83b.py::test_pipeline_orchestrator_remains_unchanged tests/test_thread_reports_ag86a.py::test_normal_author_prompt_and_orchestrator_surfaces_unchanged_by_report_module -q`
- `pytest -q`
- `python -m ruff check .`
- `python -m py_compile core/pipeline_orchestrator.py core/query_plan.py core/query_plan_runtime_adapter.py`
- `git diff --check`

## Protected surfaces kept closed

AG-91B did not change:

- router prompt text or router retry prompt text;
- recon rewriter prompt text;
- researcher prompt text;
- expander/evaluator prompts;
- any `ask_model(...)`, `brave_reconnaissance(...)`, or `embed_texts(...)` call
  shape;
- provider availability/order/roles/diagnostics;
- `select_providers(...)`;
- search-depth or supplemental-depth logic;
- query text/order semantics;
- retrieval execution, ranking/filtering, passage merge order;
- source-class recovery execution;
- conflict-resolution execution;
- final evidence bundle behavior;
- citation formatting;
- Author behavior;
- persistence, cache, or ProjectSource retrieval.

No live validation/provider/model/search/embedding calls were run.

## Remaining AG-91C/91D/91E candidates

Potential follow-ups remain separate authority/product phases:

1. Provider/depth authority mapping or collapse, only with explicit parity guards.
2. Continued demotion of compatibility trace mirrors where consumers can be
   proven to use QueryPlan-native trace keys.
3. Additional runtime-shell thinning around deterministic projection only,
   without touching provider, prompt, retrieval, final-evidence, citation, or
   persistence behavior.
