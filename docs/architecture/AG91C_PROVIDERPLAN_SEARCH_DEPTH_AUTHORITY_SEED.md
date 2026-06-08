# AG-91C ProviderPlan / Search-Depth Authority Seed

Status: behavior-preserving authority-boundary seed; no live validation; no provider/model/search/embedding calls

Branch: `ag-91c-providerplan-search-depth-authority-seed`
Base: `main`

## Purpose

AG-91C seeds a run-local `ProviderPlan` boundary for the existing provider and
search-depth path.  The phase does not redesign provider routing, change search
quality, add providers, change query generation, or alter prompt/model behavior.
It records already-selected provider/depth facts and makes the main retrieval
loop consume those facts from a single plan record instead of keeping provider
and depth facts as a purely orchestrator-local mirror.

## Inspected provider/depth path

The inspected path was the AG-91A/AG-91B pre-retrieval and retrieval-loop provider
surface:

- provider availability snapshot for Tavily, Linkup, and Exa boolean presence;
- `choose_retrieval_search_depth(...)` for main retrieval;
- `choose_supplemental_search_depth(...)` for legacy supplemental retrieval;
- `merge_search_provider_overrides(...)` and `select_providers(...)` in
  `core.routing`;
- main-loop provider/depth selection before retrieval dispatch;
- Scout/Expander continuation provider inputs;
- supplemental and Scrutineer remediation provider/depth injection through
  `legacy_review_runtime_stage`;
- provider diagnostics compatibility through unchanged dispatch/runtime payloads.

## Old local authority path demoted

Before AG-91C, the main retrieval loop chose `current_search_depth`, merged
provider overrides, selected `loop_providers`, and then passed those locals to
dispatch.  AG-91C demotes that local mirror for the main retrieval loop: the
orchestrator still owns sequencing, but the selected providers and depth consumed
by dispatch now come from a `ProviderPlanRecord` created for the pass.

The compatibility locals remain only as downstream runtime names expected by
existing helpers (`current_search_depth`, `loop_providers`,
`current_search_depth_for_recovery`).  They are now assigned from the consumed
plan record, not independently selected in parallel.

## New consumed ProviderPlan path

`core.provider_plan` adds:

- `ProviderAvailabilitySnapshot`, a JSON-safe boolean shape for the existing
  Tavily/Linkup/Exa availability keys;
- `ProviderPlanRecord`, a single role-scoped provider/depth record with trace
  projection;
- `ProviderPlan`, a run-local list of records and helper for the existing main
  retrieval selection path.

For main retrieval, the path is now:

1. build a `ProviderPlan` from the existing boolean availability snapshot;
2. call `ProviderPlan.record_main_retrieval(...)` with the same inputs used by
   the old orchestrator-local path;
3. inside the plan helper, delegate to the existing depth chooser and
   `core.routing` selectors with unchanged arguments;
4. consume `provider_plan_record.search_depth` and
   `provider_plan_record.providers_list()` for dispatch-facing locals.

## Exact parity proof

The implementation is deliberately limited to one consumed seam so parity can be
proven:

- availability projection preserves the existing `{"tavily", "linkup", "exa"}`
  boolean key shape and order;
- representative Fast/Balanced/Deep/high-complexity depth cases match
  `choose_retrieval_search_depth(...)` exactly;
- override merging and selected provider order match
  `merge_search_provider_overrides(...)` plus `select_providers(...)` exactly;
- Scout/Expander internal override behavior remains untouched and is covered by
  direct selector parity tests;
- supplemental depth/provider injection remains untouched and is covered by
  direct chooser/selector parity tests;
- `ProviderPlan.to_trace()` matches the consumed provider and depth values;
- retrieval dispatch receives the same providers/depth when fed from the plan
  record.

## Protected surfaces kept closed

AG-91C intentionally does not change:

- provider order or provider availability semantics;
- provider names or provider integrations;
- search-depth strings or escalation policy;
- supplemental-depth behavior;
- query generation, query mutation, `QueryPlan`, or prompt text;
- retrieval execution, ranking/filtering, final evidence selection, citation
  formatting, Author behavior, persistence, cache, or ProjectSource retrieval;
- provider diagnostics payload shape.

## Static guard

`core.provider_plan` is pure authority-boundary bookkeeping. It does not import
prompt modules, model-call modules, search execution functions, citation/final
answer modules, Author modules, persistence/cache modules, or ProjectSource
retrieval. It does not call `ask_model`, `process_search_queries`, `embed_texts`,
`brave_reconnaissance`, citation formatting, final evidence selection, or
persistence side effects. It introduces no new provider names beyond the existing
Tavily/Linkup/Exa context.

## Tests run

AG-91C added focused tests in `tests/test_provider_plan_ag91c.py` for:

- provider availability snapshot shape;
- main-loop search-depth parity;
- provider override merge and provider selection order parity;
- Scout/Expander internal override behavior (untouched selector parity);
- supplemental-depth/provider injection parity (untouched legacy seam);
- ProviderPlan trace/projection parity with consumed values;
- dispatch consumption of plan-selected providers/depth;
- static guard protection for `core.provider_plan`;
- static verification that the main loop consumes `ProviderPlanRecord` outputs.

## Remaining AG-91D / AG-91E candidates

Recommended follow-up candidates, still requiring explicit parity gates:

1. Add a ProviderPlan record for Scout continuation provider inputs and consume
   it only if internal override parity can be proven for all complexity/availability
   cases.
2. Add a ProviderPlan record for Expander continuation provider inputs and
   consume it only if provider order remains byte-for-byte equivalent.
3. Add legacy supplemental and Scrutineer remediation records, probably by
   passing a narrow plan facade into `legacy_review_runtime_stage`, while keeping
   the stage as an executor of already-selected facts rather than a routing brain.
4. Add diagnostics trace attachment for ProviderPlan projection if needed, without
   changing existing provider diagnostics payload fields.
