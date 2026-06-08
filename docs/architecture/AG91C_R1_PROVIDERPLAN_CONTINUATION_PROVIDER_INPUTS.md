# AG-91C-R1 ProviderPlan Continuation Provider Inputs

Status: behavior-preserving ProviderPlan authority-boundary follow-up; no live validation; no provider/model/search/embedding calls

Branch: `ag-91c-r1-providerplan-continuation-provider-inputs`
Base: `main`

## Purpose

AG-91C-R1 extends the AG-91C `ProviderPlan` boundary from the main retrieval
provider/depth selection into the Scout and Expander continuation provider-input
paths.  The phase is deliberately narrow: it records the already-existing
continuation provider selections and makes the orchestrator consume those
`ProviderPlanRecord` values for `force_component_providers`.

This is not a provider redesign, Scout/Expander behavior phase, query phase,
search-quality phase, prompt phase, or new provider integration.

## Touched continuation paths

### Scout directed continuation

The Scout directed continuation path remains responsible for producing and
authorizing Scout-directed queries exactly as before.  After authorization, the
old local provider-input path selected forced component providers with:

- existing `select_providers(...)`;
- the existing Scout override `override=["exa", "linkup"]`;
- `override_is_user=False`;
- unchanged `query_type`, `intent`, `complexity`, `available_keys`,
  `report_type`, `is_academic`, and `suppress_tavily` inputs.

AG-91C-R1 subordinates that local selection to
`ProviderPlan.record_continuation(role="scout_continuation", ...)`.  The helper
delegates to the same selector with the same arguments, records the result, and
returns a `ProviderPlanRecord`.  The orchestrator assigns
`force_component_providers` from `scout_provider_plan_record.providers_list()`.

### Expander component continuation

The Expander component continuation path remains responsible for prompt
assembly, model parsing, query finalization, and continuation authorization
exactly as before.  After authorization, the old local provider-input path
selected forced component providers with:

- existing `select_providers(...)`;
- `override=None`;
- unchanged `query_type`, `intent`, `complexity`, `available_keys`,
  `report_type`, `is_academic`, and `suppress_tavily` inputs.

AG-91C-R1 subordinates that local selection to
`ProviderPlan.record_continuation(role="expander_continuation", ...)`.  The
orchestrator assigns `force_component_providers` from
`expander_provider_plan_record.providers_list()`.

## Old provider-input path demoted/subordinated

Before this follow-up, Scout and Expander continuation branches computed
`force_component_providers` directly in `core.pipeline_orchestrator` by calling
`select_providers(...)`.  Those locals were then consumed by the next main-loop
pass as `scout_override` input to `ProviderPlan.record_main_retrieval(...)`,
which still performs the existing `merge_search_provider_overrides(...)` step.

After this follow-up, the compatibility local `force_component_providers`
remains, but for the touched Scout and Expander branches it is assigned from a
consumed `ProviderPlanRecord`.  The next-pass merge and retrieval dispatch path
remain unchanged.

## New consumed ProviderPlan path

`core.provider_plan.ProviderPlan.record_continuation(...)` is a narrow record
helper for continuation provider inputs.  It:

1. projects the existing Tavily/Linkup/Exa availability keys from the run-local
   plan;
2. delegates provider selection to the existing selector supplied by the
   orchestrator;
3. preserves the existing selector call shape and keyword arguments;
4. records role, providers, optional override, availability, and JSON-safe
   selection inputs;
5. returns a `ProviderPlanRecord` that the orchestrator consumes immediately.

The helper does not choose search depth, merge main-loop provider overrides,
execute search, call models, mutate queries, inspect prompts, or introduce any
provider policy.

## Exact parity proof

Focused tests prove the consumed continuation records preserve the old values:

- Scout continuation parity covers representative availability and complexity
  cases, including medium complexity Linkup suppression, high complexity
  Linkup admission, unavailable Exa/Linkup filtering, and all-provider-unavailable
  fallback behavior.
- Expander continuation parity covers default provider selection across medium
  and high complexity, benchmark/report-type influence, academic selection, and
  Tavily suppression cases.
- ProviderPlan trace/projection tests assert recorded Scout and Expander
  continuation providers match the consumed provider values and preserve the
  Scout override projection.
- Dispatch-facing parity is covered by feeding the recorded continuation
  providers into the existing main-loop `record_main_retrieval(...)` merge path
  and comparing the resulting providers with the old local continuation
  selection plus old merge/selection sequence.
- Existing main retrieval ProviderPlan tests continue to cover depth selection,
  override merge order, provider order, trace projection, and dispatch
  consumption.

## Protected surfaces kept closed

AG-91C-R1 intentionally does not change:

- Scout prompt text, Scout query behavior, or Scout firing conditions;
- Expander prompt text, Expander query behavior, or Expander firing conditions;
- query generation, query mutation, `QueryPlan`, or query ordering;
- provider order, provider availability semantics, provider names, or provider
  integrations;
- search-depth strings or search-depth escalation behavior;
- supplemental-depth behavior, Scrutineer remediation, retrieval execution,
  ranking/filtering, final evidence selection, citation formatting, Author
  behavior, persistence, cache, or ProjectSource behavior.

## Static guard

`core.provider_plan` remains authority-boundary bookkeeping only.  Static tests
continue to guard against imports or calls for model execution, search execution,
embeddings, prompt modules, citation/final-evidence modules, persistence/cache,
ProjectSource, and new provider surfaces.

## Remaining AG-91D / AG-91E candidates

Potential follow-up candidates, still requiring explicit parity gates:

1. attach `ProviderPlan.to_trace()` into a broader diagnostics projection if a
   later observability phase requests it;
2. add legacy supplemental-depth/provider records only with a narrow facade into
   the legacy review runtime and no change to supplemental depth behavior;
3. evaluate Scrutineer remediation provider inputs as a separate phase after
   Scout/Expander continuation records remain stable;
4. keep provider allocation and query-authority phases separate so ProviderPlan
   does not become a provider-routing brain.
