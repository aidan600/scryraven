Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96E2_COMPONENT_AWARE_QUERYPLAN_CONSUMPTION).

# AG-96E2 Component-Aware QueryPlan Consumption

## Status

AG-96E2 is the first protected QueryPlan-consumption phase for SearchWorkPlan.
It makes QueryPlan consume the SearchWork shadow projection only for admission
and ordering of already-existing candidate query strings.

The phase does not generate executable query text, change prompts, select
providers, choose search depth, execute search or retrieval, alter citation
behavior, satisfy source obligations, change final-answer behavior, or activate
QuantWorkUnit/source-value extraction.

## Why This Is First

AG-96C built the passive SearchWorkPlan contract, RunKernel shadow construction,
and QueryPlan-work shadow projection. AG-96D made official/current source
obligations visible to recovery-compatible handoffs. AG-96E1 replaced the
conservative scaffold with deterministic query-shape and contract-resolution
records, but QueryPlan still did not consume the result.

AG-96E2 opens the smallest safe runtime consumer: QueryPlan admission/order.
That is enough to prevent obvious multipart components from starving under a
crude global candidate cap, while leaving query generation and execution
authorities closed.

## What QueryPlan May Consume

QueryPlan may read safe SearchWork projection fields:

- component ids and component rank;
- component subquestion tokens when present;
- source-obligation ids, kinds, and required source-class hints;
- provider-job ids and provider-job kinds as non-executing hints;
- existing route/core-topic/entity facts already available to QueryPlan.

The helper records a trace-safe allocation result with considered component,
source-obligation, and provider-job ids; admitted query order; rejected
over-budget queries; unfilled components; and explicit behavior-boundary flags.

## Admission And Order

The allocation helper receives only existing candidate query strings. It
deterministically matches those strings against component/source/provider-job
tokens, then orders candidates coverage-first:

1. admit at most one matching query for each ranked component;
2. fill remaining slots with the remaining existing candidates in prior order;
3. respect the existing `max_len` cap;
4. record components without admitted coverage as unfilled gaps.

If a component has no matching candidate, QueryPlan records the gap. It does not
invent a query.

## Closed Boundaries

Query text generation remains closed. SearchWork may influence which existing
candidate strings are admitted and in what order, but it cannot synthesize a new
string.

Provider jobs remain hints only. Provider-job ids and kinds can appear as
QueryPlan metadata, but they do not select providers, choose depth, run search,
or execute retrieval.

Source obligations are not satisfied here. Official/current, legal/current
primary, canonical documentation, and source-bound numeric obligations remain
EvidenceLedger/custody and downstream judgment concerns. QueryPlan metadata is
planning/admission metadata only.

## Fallback

When no SearchWork projection is supplied, QueryPlan behavior remains unchanged.
When a supplied projection is malformed or unusable, QueryPlan records a
fallback reason and preserves the existing query order.

## Deferred

Still deferred:

- executable query text generation from SearchWorkPlan;
- provider-job execution;
- provider routing or depth-policy changes;
- retrieval ranking/filtering changes;
- prompt changes;
- citation and final-answer behavior changes;
- source-obligation satisfaction and evidence custody;
- QuantWorkUnit extraction/calculation execution;
- D3 recovery activation gating changes;
- Fast official lane runtime demotion.
