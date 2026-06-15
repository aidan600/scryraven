# AG-96E1 Real QueryShape And Contract Resolution

## Status

AG-96E1 replaces the conservative runtime SearchWorkPlan shadow scaffolding with
a deterministic runtime query-shape classifier and contract resolver at
`core/search_work_query_shape_runtime.py`.

The result remains shadow/projection-only. `QueryPlan` still does not consume
`SearchWorkPlan`; provider/search/retrieval execution, query text generation,
prompts, final answers, citations, mode policy, and Fast official lane runtime
behavior remain unchanged.

## Why This Replaces Scaffolding

AG-96C8/C10 proved that the runtime could construct a RunKernel-owned
`SearchWorkPlan` shadow after RunAuthority contract synthesis, but the helper
deliberately emitted one conservative component and marked:

- `implements_query_shape_classifier: false`;
- `implements_contract_resolver: false`.

AG-96E1 keeps the same RunKernel shadow construction seam and D-series downstream
handoff chain, but now fills the AG-96C records from deterministic safe runtime
facts. The old conservative scaffold remains as a fallback if the deterministic
records cannot validate.

## Allowed Inputs

The classifier/resolver may use only safe facts already available after contract
synthesis:

- requested mode;
- selected depth;
- sanitized RunAuthority contract projection;
- sanitized route facts;
- current-date reference;
- safe user query preview when supplied by the lane call.

It must not access secrets, raw prompts, raw provider payloads, raw model
responses, DB rows, private logs, caches, full traces, local output packets, or
live provider/model/search/retrieval systems.

## Detected Shape Categories

The deterministic classifier can mark:

- simple lookup;
- official/current lookup;
- legal/current-primary;
- canonical documentation;
- source-bound numeric;
- time-sensitive/currentness;
- conflict/reconciliation likely;
- obvious multipart/component structure.

Multipart detection now creates multiple component candidates for obvious
component questions, including current official fee plus legal deadline plus API
parameter, comparisons using official/current sources, and numeric-rate plus
calculation questions.

## Obligations And Hints

Source-obligation candidates are derived for:

- `official_current`;
- `legal_current_primary`;
- `canonical_documentation`;
- `source_bound_numeric`;
- `conflict_resolution` when conflict/reconciliation is likely;
- `reputable_secondary` only when no stricter obligation is indicated.

Official/current, legal/current-primary, canonical-documentation,
source-bound-numeric, and conflict-resolution obligations remain required and do
not allow lower-tier final satisfaction.

Provider-job candidates remain hints only. AG-96E1 may emit:

- `official_candidate_acquisition`;
- `canonical_extraction`;
- `fetch_read_extract`;
- `conflict_currentness_check`;
- `direct_candidate_search`.

All provider jobs are non-executing hints. They do not select providers, generate
queries, choose depth, run search, run retrieval, or satisfy source obligations.

## Contract Resolution

The resolver records the requested mode and maps answer contracts deterministically:

- Fast -> `direct_constrained`;
- Balanced -> `explanatory`;
- Deep -> `research_reconciliation`.

If the query shape appears more complex than the requested mode, the resolver
records mismatch/pressure in shadow state. It does not mutate selected runtime
mode, spend a deeper budget, or change QueryPlan behavior.

## QueryPlan Boundary

`QueryPlan` remains the executable query identity, order, and admission owner.
AG-96E1 does not make QueryPlan consume `SearchWorkPlan`, does not generate
executable query text, and does not alter query admission/order behavior.

The lane projection continues to mark behavior-changing flags false, including
QueryPlan, query text, provider/search, retrieval, prompt, citation, and final
answer behavior flags.

## D-Series Downstream Chain

AG-96D0/D1/D2/D3 continue downstream from SearchWork source obligations:

```text
SearchWorkPlan shadow projection
-> QueryPlan-work shadow projection
-> official/current handoff
-> recovery bridge
-> gated activation helper
```

AG-96E1 improves the plan inputs to that chain. It does not alter D0 handoff
semantics, D1 lane visibility, D2 bridge semantics, D3 activation gating, or the
Fast official lane runtime path.

## Deferred

Still deferred:

- QueryPlan consumption of SearchWorkPlan;
- executable query generation from SearchWorkPlan;
- provider-job execution;
- provider routing or depth-policy changes;
- source-obligation satisfaction from fetched evidence;
- prompt, citation, final-answer, or Author behavior changes;
- live provider/model/search/retrieval validation;
- Fast official lane runtime demotion or deletion.
