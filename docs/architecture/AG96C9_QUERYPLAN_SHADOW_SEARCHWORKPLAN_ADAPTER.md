# AG-96C9 QueryPlan Shadow SearchWorkPlan Adapter

## Status

AG-96C9 adds a pure, behavior-preserving adapter at
`core/search_work_plan_query_plan_shadow.py`.

The adapter translates a safe `SearchWorkPlan` projection, or a RunKernel
trace-shaped mapping that contains one, into a JSON-safe QueryPlan-adjacent
shadow projection. It is not wired into production runtime.

## Projection

The projection is named `query_plan_work_shadow_projection`.

It summarizes:

- components;
- source obligations by component;
- provider-job needs by component;
- official/current, legal/current, canonical-documentation, and source-bound
  numeric acquisition needs;
- quant, synthesis, and audit work counts;
- stop-condition and follow-up posture;
- candidate work groups.

It does not include executable query text or user-facing component prose.

## Behavior Boundary

The adapter sets explicit no-behavior-change flags:

- `shadow_only: true`
- `runtime_consumed_by_query_plan: false`
- `query_plan_behavior_changed: false`
- `query_text_generated: false`
- `query_admission_changed: false`
- `provider_search_behavior_changed: false`

It also records that query order, search depth, retrieval, prompts, citations,
and final answers are unchanged.

## Deferred Runtime Wiring

AG-96C8 already wires runtime SearchWorkPlan shadow construction after
RunAuthority contract synthesis. AG-96C9 intentionally does not add a
`pipeline_orchestrator.py`, RunKernel, QueryPlan, query-production, provider,
search, retrieval, or prompt callsite.

Any future runtime consumption of this projection needs a separate phase that
reopens the relevant runtime surface and proves behavior boundaries again.

## Static Boundary

Tests assert that production runtime modules do not import or call the adapter,
and that the adapter does not import QueryPlan, provider/search/retrieval,
prompt, RunKernel, or orchestrator surfaces.

## Non-Goals

AG-96C9 does not change QueryPlan behavior, query text generation, query
admission, query ordering, provider selection, search depth, retrieval, prompts,
citations, final answers, mode policy, live calls, or private/raw artifact
handling.
