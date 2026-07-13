Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96C8_RUNTIME_SHADOW_SEARCHWORKPLAN_CALLSITE).

# AG-96C8 Runtime Shadow SearchWorkPlan Callsite

## Status

AG-96C8 wires the AG-96C7 RunKernel shadow `SearchWorkPlan` construction seam
into the real runtime path after RunAuthority contract synthesis.

The callsite is projection-only. It does not change QueryPlan behavior, query
text, query order, query admission, provider selection, search depth, retrieval,
prompts, citations, final answers, mode policy, or specialist behavior. No live
provider, model, search, retrieval, or validation calls are part of this phase.

## Runtime Seam

The runtime callsite is in `core/pipeline_orchestrator.py` immediately after:

```text
run_kernel.reduce(run_contract_result.observation)
run_contract_projection = dict(run_kernel.state.run_contract_projection)
```

It performs only:

```text
RunKernel.authorize_search_work_plan_construction(...)
-> observe_runtime_shadow_search_work_plan_construction(...)
-> RunKernel.reduce(...)
```

The orchestrator passes already-available structured facts into
`core/search_work_plan_shadow_runtime.py`. It does not build plan semantics,
classify query shape, resolve contracts, generate query text, choose providers,
or alter downstream policy.

## Helper Boundary

`core/search_work_plan_shadow_runtime.py` is a bounded runtime-shadow helper.
It derives conservative AG-96C6 construction records from:

- canonical `run_contract_projection`;
- compact route projection facts already reduced into RunKernel state;
- requested mode / selected depth already present;
- current-date refs;
- schema/version metadata.

The helper explicitly marks the resulting records as runtime shadow
scaffolding. It does not implement a real `QueryShapeClassifier` or
`ContractResolver`.

## Projection State

Reduction stores canonical RunKernel shadow state at:

- `RunState.search_work_plan`;
- `RunState.search_work_plan_projection`;
- `RunState.search_work_plan_validation`;
- `RunState.projections["search_work_plan_construction"]`.

The projection remains unconsumed by QueryPlan and carries no-behavior-change
flags, including `runtime_consumed_by_query_plan: false`,
`provider_search_behavior_changed: false`,
`query_plan_behavior_changed: false`, `prompt_behavior_changed: false`, and
`final_answer_behavior_changed: false`.

## Boundary Proof

Focused tests cover:

- post-contract runtime-shadow construction and RunKernel trace projection;
- QueryPlan/query-production behavior unchanged by the shadow projection;
- pass-through-only orchestrator callsite ordering;
- sensitive field/key omission for raw/private inputs;
- static guards preventing QueryPlan/provider/prompt modules from importing the
  runtime-shadow helper;
- static guards preventing the helper from importing provider/search/retrieval,
  prompt, QueryPlan, or orchestrator surfaces.

## Old Path Status

The old executable query identity/order owner remains QueryPlan. The old
provider/search/retrieval and prompt/final-answer paths remain closed and
unchanged. This phase adds canonical RunKernel shadow state only; future
activation of any QueryPlan/provider relationship requires a separately scoped
phase.
