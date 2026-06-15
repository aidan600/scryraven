# AG-96C10 Consolidated SearchWork Shadow Lane

## Status

AG-96C10 replaces the inline AG-96C8 SearchWorkPlan shadow construction block in
`core/pipeline_orchestrator.py` with a single consolidated lane runner at
`core/search_work_shadow_lane_runtime.py`.

The lane is shadow infrastructure only. It does not change QueryPlan behavior,
query text generation, query admission/order, provider selection, search depth,
retrieval, prompts, citations, final answers, mode policy, specialist behavior,
official/current acquisition behavior, or live validation.

## Why the lane exists

AG-96C8 proved that the runtime can construct a RunKernel-owned
`SearchWorkPlan` shadow after RunAuthority contract synthesis. AG-96C9 proved
that a safe `SearchWorkPlan` projection can be translated into a QueryPlan-work
shadow projection. Leaving those as separate orchestrator callsites would make
`pipeline_orchestrator.py` accumulate one-off shadow glue.

AG-96C10 makes the orchestrator a pass-through caller:

```text
RunAuthority contract reduced
-> run_search_work_shadow_lane(...)
-> production QueryPlan/query generation continues unchanged
```

The lane owns the shadow/projection semantics. The orchestrator supplies only
safe runtime refs and facts already available after contract synthesis.

## What it consolidates

`run_search_work_shadow_lane(...)` performs two bounded steps:

1. Authorize, observe, and reduce SearchWorkPlan shadow construction through the
   existing AG-96C7/C8 APIs.
2. Derive `query_plan_work_shadow_projection` through the existing AG-96C9
   adapter from the constructed RunKernel SearchWorkPlan state.

The resulting lane projection records:

- `shadow_lane_ran: true`;
- whether the SearchWorkPlan and QueryPlan-work projections are present;
- the nested QueryPlan-work shadow projection;
- no-behavior-change flags for QueryPlan, query text/admission/order,
  provider/search, retrieval, prompt, citation, and final-answer behavior.

The lane stores only a projection entry under RunKernel state. It does not add
QueryPlan consumption or provider/search scheduling authority.

## Behavior boundary

The lane marks all behavior-changing flags false and keeps executable runtime
ownership unchanged:

- QueryPlan remains the executable query identity/order/admission owner.
- Provider/search/retrieval modules do not import or consume the lane.
- Prompt, citation, and final-answer modules do not import or consume the lane.
- The QueryPlan-work projection contains work hints only; it contains no
  executable query text and admits no candidates.
- Raw/private fields such as raw prompts, raw provider payloads, raw model
  responses, secrets, tokens, DB rows, and full traces are removed from lane
  output.

## Deferred work

Deferred phases must separately license any production consumption of
SearchWorkPlan or QueryPlan-work shadow state. That includes query admission,
query generation, provider-job scheduling, source-obligation acquisition,
official/current validation, retrieval behavior, prompt changes, citation
behavior, final-answer readiness, and live validation.
