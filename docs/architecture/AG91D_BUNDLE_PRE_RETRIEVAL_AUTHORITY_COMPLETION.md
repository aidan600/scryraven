# AG-91D Bundle: Pre-Retrieval Authority Completion

Status: implementation complete; behavior-preserving; no live validation

Branch: `ag-91d-bundle-pre-retrieval-authority-completion`
Base: `main`

## Purpose

AG-91D completes the remaining pre-retrieval authority-boundary work without changing product behavior, prompt text, provider routing, search depth policy, query text/order, embedding configuration, retrieval execution, ranking/filtering, final evidence, citations, Author behavior, persistence, cache, or ProjectSource behavior.

The phase adds consumed runtime authority records at three narrow seams:

1. ProviderPlan records for synthesis-evaluator supplemental search and Scrutineer remediation provider/depth inputs.
2. QueryPlan admission methods for recon-rewriter and researcher pre-retrieval query candidates.
3. Explicit embedding and retrieval action records consumed by existing runtime callsites.

## Stage 0 — Static inventory and implementation plan

The implementation inventory confirmed narrow consumed-authority seams already existed:

- `legacy_review_runtime_stage` selected supplemental and Scrutineer providers/depths immediately before dispatch.
- `pipeline_orchestrator` held recon and researcher candidate locals before `QueryPlan` finalization.
- the embedding kickoff was a single direct `embed_texts(...)` call for `_embed_topic`.
- `retrieval_dispatch_runtime` already had `RecordedRetrievalDispatch` for mechanical dispatch records and could reuse it for main retrieval pass consumption.

No behavior edits were made before these seams were identified.

## Stage 1 — ProviderPlan supplemental/Scrutineer completion

### Touched surfaces

- `core.provider_plan`
- `core.legacy_review_runtime_stage`
- provider-plan parity tests

### Old authority path demoted

Before this stage, `legacy_review_runtime_stage` directly called the injected `choose_supplemental_search_depth(...)` and `select_providers(...)` functions for supplemental search, and directly called `select_providers(...)` for Scrutineer remediation.

After this stage, those calls are subordinate to ProviderPlan records:

- `ProviderPlan.record_supplemental_retrieval(...)`
- `ProviderPlan.record_scrutineer_remediation(...)`

The records delegate to the same injected selectors with the same inputs and are then immediately consumed for runtime dispatch fields.

### New authority owner

`ProviderPlan` owns provider/depth bookkeeping only. It does not choose new provider policy, inspect prompts, execute search, call models, rank evidence, or alter retrieval.

### Runtime consumers

- Supplemental search consumes `supplemental_provider_record.search_depth` and `supplemental_provider_record.providers_list()`.
- Scrutineer remediation consumes `remediation_provider_record.providers_list()` and records the unchanged search depth.

## Stage 2 — Recon / router / researcher query admission collapse

### Touched surfaces

- `core.query_plan_runtime_adapter`
- `core.pipeline_orchestrator`
- QueryPlan parity tests

### Old authority path demoted

Before this stage, recon and researcher output was stored in a local `queries` variable and later finalized with a generic QueryPlan call.

After this stage:

- recon output is held as `pre_retrieval_query_candidates` and admitted through `QueryPlanRuntimeAdapter.admit_recon_candidates(...)`;
- researcher fallback output is held as `researcher_query_candidates` and admitted through `QueryPlanRuntimeAdapter.admit_researcher_candidates(...)`;
- recency merge and final execution admission remain QueryPlan-owned;
- `queries_by_iteration` remains derived from `QueryPlan.queries_by_iteration()`.

Router retry/entity correction remains documented as a router-state normalization input. It does not directly produce final retrieval queries in this phase; downstream query-affecting candidates are admitted through QueryPlan before retrieval consumption.

### New authority owner

`QueryPlan` remains the query admission and ordering authority only. It does not own provider/depth selection, search execution, prompt assembly, model calls, citations, final evidence, persistence, cache, or ProjectSource behavior.

### Runtime consumers

- Initial retrieval `current_queries` is derived from QueryPlan-admitted recon or researcher candidates.
- The retrieval loop consumes `query_authority.admit_execution_queries(...)` output before dispatch.

## Stage 3 — Embedding / retrieval action authorization boundary

### Touched surfaces

- `core.retrieval_dispatch_runtime`
- `core.pipeline_orchestrator`
- retrieval dispatch/action tests

### Old authority path demoted

Before this stage, embedding kickoff called `embed_texts(...)` directly from local orchestrator fields. Main retrieval pass descriptor/envelope/pass-record assembly also read local scope fields directly.

After this stage:

- embedding kickoff builds an `EmbeddingActionRecord` and calls `execute_embedding_action(...)`;
- main retrieval pass builds a `RecordedRetrievalDispatch` action and consumes its fields for descriptor, execution envelope, handoff kwargs, and pass records;
- existing supplemental, remediation, disambiguation, recovery, and conflict-resolution helper dispatch paths continue to use recorded dispatch/action inputs where already present.

### New authority owners

- `EmbeddingActionRecord` owns the already-authorized embedding topic/provider/model/base URL fields for the kickoff call.
- `RecordedRetrievalDispatch` owns already-authorized retrieval queries, providers, depth, result count, include/exclude domains, provider role, iteration, domain filters, entity hint, and similarity fields for main retrieval dispatch consumption.

### Runtime consumers

- `execute_embedding_action(...)` consumes `EmbeddingActionRecord.topic_text`, `.provider`, `.model`, and `.base_url` for the existing `embed_texts(...)` call shape.
- `execute_main_retrieval_pass_from_scope(...)` consumes `RecordedRetrievalDispatch` fields when building retrieval descriptors, envelopes, execution handoff arguments, and pass records.

## Behavior-preservation proof

The implementation preserves exact runtime values:

- ProviderPlan supplemental tests compare recorded search depth against `choose_supplemental_search_depth(...)` and recorded providers against `select_providers(...)` for representative complexity, availability, academic/report-type, suppress-Tavily, and override cases.
- QueryPlan tests compare recon and researcher admission output against the legacy `finalize_retrieval_queries(...)` facade and verify recency merge, official/canonical bias separation, and retrieval-loop consumption order.
- Embedding action tests assert the exact topic/provider/model/base-url call mapping.
- Retrieval dispatch action tests assert exact query, provider, depth, result count, include/exclude domain, provider-role, iteration, entity-hint, and similarity-field preservation.
- Legacy review, routing, weak-corpus, source-class, and retrieval-stop targeted tests were run without live provider/model/search/embedding calls.

## Protected surfaces kept closed

This phase did not change:

- router, router retry, recon rewriter, researcher, Scout, Expander, Evaluator, Economist, Scrutineer, Analyst, or Author prompt text;
- any `ask_model(...)` call shape;
- any `brave_reconnaissance(...)` call shape;
- embedding topic/provider/model/base URL/cadence;
- provider names, availability semantics, ordering, routing behavior, swaps, or integrations;
- search-depth strings or escalation policy;
- query text/order behavior;
- retrieval execution, ranking/filtering, passage merge order, source-class recovery, conflict resolution, final evidence, citations, Author behavior, persistence, cache, or ProjectSource behavior.

## Static guards

Static tests guard that:

- ProviderPlan remains bookkeeping/selector-delegation only and imports no prompt/model/search execution, citation/final-evidence, persistence/cache, or ProjectSource surfaces.
- QueryPlan and its runtime adapter do not import/call provider/search execution, prompts, model calls, embeddings, final evidence, citation, persistence, cache, or ProjectSource surfaces.
- Retrieval dispatch/action records do not import routing, prompts, model providers, provider policy, or search-depth policy.

## Tests run

- `pytest -q tests/test_provider_plan_ag91c.py`
- `pytest -q tests/test_query_plan_ag89c.py`
- `pytest -q tests/test_ag90d_retrieval_dispatch_runtime.py`
- `pytest -q tests/test_routing.py`
- targeted legacy review/Scrutineer/supplemental/retrieval-stop/weak-corpus/source-class tests
- `pytest -q`
- `python -m ruff check .`
- `python -m py_compile core/pipeline_orchestrator.py core/provider_plan.py core/query_plan.py core/query_plan_runtime_adapter.py core/retrieval_dispatch_runtime.py core/legacy_review_runtime_stage.py`
- `git diff --check`

## Remaining known authority debt

- Router retry/entity correction remains router-state normalization. It is not a final-query authority path in this phase, but any future query-affecting router candidate expansion should be admitted explicitly through QueryPlan.
- Source-class recovery action queries remain owned by the Controller/RunAuthority
  recovery action envelope. AG-91D did not collapse that action-query ownership
  into QueryPlan; a future phase may choose to unify recovery action query
  projection explicitly.
- Recovery/conflict-resolution action paths already have bounded helper records/context seams; a later phase could further unify their action projection if useful, without creating a generic RunAuthority framework.

## Recommended next action

Review AG-91D as a behavior-preserving authority-boundary completion PR. If accepted, the next safe follow-up is a narrow observability pass that projects these consumed records into diagnostics without changing runtime behavior.
