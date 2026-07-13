Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG96F1_PROVIDER_JOB_EXECUTION_RECORDS).

# AG-96F1 Provider-Job Execution Records

## Status

AG-96F1 adds trace-safe provider-job execution records at
`core/search_work_provider_job_execution.py` and attaches the resulting handoff
projection to QueryPlan admission output.

The phase is an accountability and retrieval-handoff step. It does not add
providers, generate executable query text, change provider routing, change
search depth, execute retrieval, alter prompts, alter citations, change final
answer behavior, satisfy source obligations, or judge evidence sufficiency.

## Why Records Replace Hints-Only Visibility

AG-96E1 and AG-96E2 made SearchWork provider jobs visible as non-executing hints
and let QueryPlan use SearchWork metadata only to allocate already-existing query
strings. That left an accountability gap:

```text
SearchWork component
-> source obligation
-> provider-job hint
-> QueryPlan admitted query
-> existing retrieval/search handoff
```

AG-96F1 fills the missing middle step with explicit execution records:

```text
SearchWork component
-> source obligation
-> provider-job hint
-> QueryPlan admitted query
-> provider-job execution record
-> existing retrieval/search handoff
```

The record is not a new executor. It is a trace-safe handoff contract showing
which QueryPlan-admitted query string carries a provider-job hint into the
existing retrieval loop.

## Record Claims

Each provider-job execution record can claim:

- the SearchWork component id;
- the source obligation ids associated with the provider-job hint;
- the provider job id and kind;
- the QueryPlan item ids that admitted matching existing query strings;
- the ordinary authorized query strings handed to retrieval;
- whether the job is `admitted`, `deferred`, or `unmatched`;
- that execution ownership remains `existing_retrieval_loop`;
- that the helper did not select providers, run search, run retrieval, or create
  evidence refs.

Behavior-boundary flags remain false for query-text generation, provider
selection, provider/search behavior changes, retrieval behavior changes, prompt
behavior changes, citation behavior changes, final-answer behavior changes,
source obligation satisfaction, and official/current custody satisfaction.

## Record Non-Claims

Execution records do not claim:

- provider execution success;
- source obligation satisfaction;
- official/current source custody completion;
- evidence sufficiency;
- citation eligibility;
- final-answer readiness;
- QuantWorkUnit extraction or calculation;
- provider routing or depth-policy authority.

Source-bound numeric records may be admitted to retrieval as ordinary query
handoff records, but numeric extraction and calculation remain explicitly false
and deferred to a future evidence/quant phase.

## Binding To QueryPlan

The helper consumes QueryPlan trace after AG-96E2 component-aware consumption.
It uses safe metadata already attached to QueryPlan items:

- `search_work_component_id`;
- `source_obligation_candidate_ids`;
- `provider_job_candidate_ids`.

When a provider-job id appears on an admitted QueryPlan item whose authorized
query is still present in the current query list, the provider-job execution
record is marked `admitted` and hands that query to the existing retrieval loop.

When a matching QueryPlan item was rejected over budget, the record is marked
`deferred`. When SearchWork shows a component with provider-job work but
QueryPlan admitted no matching query, the record is also deferred or unmatched.
No replacement query is generated.

## Existing Retrieval Remains Owner

The helper has no provider, search, retrieval, prompt, citation, or final-answer
imports. Runtime wiring occurs in QueryPlan admission, where the helper receives
already-computed SearchWork projection, QueryPlan trace, and current authorized
query strings.

The existing retrieval loop still receives the same ordinary authorized query
strings. Provider-job records only add trace accountability around that handoff.

## Evidence And Sufficiency Remain Deferred

AG-96F1 intentionally stops before evidence custody and sufficiency. Records keep
`source_obligations_satisfied=false`, `official_current_custody_satisfied=false`,
and `evidence_refs=[]`.

G1 or a later explicitly licensed phase must decide how fetched evidence,
EvidenceLedger custody, official/current source requirements, QuantWorkUnit
execution, SearchJudgment, SufficiencyJudgment, citations, and final answers
consume these records.

## Deferred

Still deferred:

- executable query text generation from SearchWork;
- provider routing or depth-policy changes;
- retrieval dispatch, ranking, or filtering changes;
- post-dispatch provider success accounting beyond optional trace refs;
- evidence custody and source-obligation satisfaction;
- official/current custody completion;
- QuantWorkUnit extraction/calculation;
- SearchJudgment and SufficiencyJudgment closure;
- prompt, citation, Author, and final-answer behavior changes;
- Fast official lane demotion or runtime rewrite.
