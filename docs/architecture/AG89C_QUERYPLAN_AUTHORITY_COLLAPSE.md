# AG-89C QueryPlan Authority Collapse

Status: bounded implementation; behavior-preserving query authority seam; no live validation

## Scope

AG-89C makes `core.query_plan.QueryPlan` the run-local authority for retrieval
query identity, query mutation/admission records, deterministic ordering, and the
query trace projection. Existing model prompts, provider routing, provider depth
policy, retrieval ranking, citation behavior, Author behavior, and final answer
behavior remain unchanged.

## Implemented seam

`QueryPlan` records:

- candidate observations from existing model/recon/retry query surfaces;
- empty and duplicate query rejections;
- deterministic finalization/admission;
- official/canonical bias as query-plan mutation metadata only;
- recency merge ordering;
- retrieval-loop ordered queries by iteration;
- recovery, continuation, supplemental, remediation, and disambiguation roles at
  the existing callsites where those queries already enter the pipeline.

The legacy `finalize_retrieval_queries(...)` API remains for compatibility, but
it is now a facade over `authorize_retrieval_queries(...)`. It no longer owns
query identity independently.

## Trace ownership

The runtime execution trace now includes `query_plan`, emitted from
`QueryPlan.to_trace_fragment()`. `queries_per_iteration` is derived from
`QueryPlan.queries_by_iteration()` after retrieval execution has admitted the
ordered query text, rather than being assembled as an independent query-authority
surface.

## Official/current custody boundary

Official/canonical query bias can be recorded with `official_bias_applied`, but
that metadata explicitly names `official_current_source_custody` as the custody
owner and records `custody_satisfied: false`. Query text, query counts, and bias
presence do not satisfy official/current/canonical source custody.

## Protected behavior

This phase does not change:

- provider selection or routing;
- provider/search-depth policy;
- model prompts or prompt text;
- retrieval ranking/filtering;
- final evidence selection;
- citation formatting;
- Author prompt/prose/final answer behavior;
- cache reuse or ProjectSource retrieval.
