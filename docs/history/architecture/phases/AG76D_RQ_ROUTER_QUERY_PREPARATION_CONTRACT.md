Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG76D_RQ_ROUTER_QUERY_PREPARATION_CONTRACT).

# AG-76D-RQ Router / Query Preparation Contract

Date: 2026-05-31

Phase type: **core authority transfer**

Mode: Architecture Groove / Prove Mode

## Licensed Protected Surface

AG-76D-RQ opens only the Router / QueryPreparation state contract surface. It
licenses passive normalization, packaging, provenance capture, controller
visibility, and a small orchestrator handoff for already-computed Router and
query-preparation facts.

It does not license prompt rewriting, Router prompt behavior changes, Researcher
prompt behavior changes, model/provider changes, query-generation changes,
query-finalization changes, provider routing/depth changes, retrieval
ranking/filtering changes, Author/final-answer/citation changes, live
validation, DB/schema changes, RunOutcome shape changes, or LLM caching.

## Reconnaissance Summary

1. `pipeline_orchestrator.py` obtained Router output by calling the fast model
   with `DEFAULT_SYSTEM["router"]`, cleaning JSON, parsing it inline, and
   lowercasing/normalizing intent, report type, image mode, query type, core
   topic, academic flag, primary entity, and entity list.
2. Intent, `report_type`, `query_type`, entities, `primary_entity`, and
   `core_topic` were derived in that inline parse block, then later modified by
   nutrition lookup override, `focus_academic`, `force_intent_news`, recon
   canonical subject promotion, and final entity normalization.
3. Entity fallback provenance lived only in the orchestrator-local call to
   `fallback_entities_from_query(query)` when Router returned no entities.
4. Router retry provenance lived only in the local `router_entity_retry_used`
   boolean and the retry branch that parsed retry Router JSON inline.
5. Routing override provenance lived in local `router_original_report_type`,
   `router_original_query_type`, `routing_override_applied`, and
   `routing_override_reason` variables.
6. Query-preparation provenance lived across local `queries`,
   `_finalize_retrieval_queries(...)`, `current_queries`, recon/researcher
   branching, recency merge logic, and `queries_by_iteration` trace fields.
7. Retrieval budget seed facts were established locally from strategy-derived
   `complexity`, `max_queries`, `results_per_query`, `search_depth`,
   `top_chunks`, and `max_iterations`.
8. Official/current/source-obligation posture became visible later through
   existing source-class recovery recommendation, source-class observability, and
   `apply_official_source_obligation_bridge(...)`; official-source query bias
   and recency-query merge posture were inferred earlier from
   `wants_official_source_bias(...)`, `official_bias_phrase(...)`, and
   `should_merge_recency_queries(...)`.
9. Some facts already flowed into AnswerContract / controller surfaces:
   `RuntimeAnswerContractFacts` consumed query, intent, report type, query type,
   mode, current date, core topic, evidence state, source-class recovery
   telemetry, lifecycle data, conflict facts, and retrieval-loop telemetry;
   controller mirrors recorded run metadata, final evidence, stage ledger
   query/provider facts, source-class recovery recommendation, and answer
   contract handoff facts.
10. Orchestrator-local authority remained for normalized Router fields, entity
    fallback/retry facts, routing override provenance, query-preparation posture,
    retrieval budget seeds, official-bias/recency posture, and the relationship
    between those facts and controller-visible state.

## Old Router / Query-Preparation Authority Path

Before AG-76D-RQ, the orchestrator was the sole authority for the normalized
Router/query-preparation posture. It parsed Router JSON inline, applied entity
fallback inline, optionally retried the Router inline, retained original Router
report/query types in locals, applied local routing overrides, generated or
accepted query lists through existing recon/researcher paths, finalized queries
through existing retrieval-quality helpers, merged recency queries inline, and
passed those local values downstream.

## New Controller-Owned Contract / State

`core.router_query_preparation_contract` now owns the passive
`RouterQueryPreparationState` contract plus deterministic builders:

- `build_router_query_preparation_state(...)` normalizes Router JSON, entity
  fallback, and retry provenance without storing raw Router payloads in trace.
- `with_router_query_runtime_posture(...)` attaches already-computed runtime
  posture: routing overrides, retrieval budget seeds, recency merge posture,
  official-source bias posture, query text/order facts, and AnswerContract /
  controller-ledger relationship notes.
- `RouterQueryPreparationState.to_trace_fragment()` exposes an additive
  `router_query_preparation_contract` packet.
- `RouterQueryPreparationState.to_controller_state()` mirrors the same sanitized
  packet into `RunController.state.route_fields`.

The contract is passive and deterministic. It imports no provider/model/search,
prompt, Author, citation, final-answer, Economist, Scrutineer, or follow-up
behavior modules.

## Mechanical Orchestrator Handoff Remaining

The orchestrator still performs the existing model calls, recon/researcher query
planning, existing query finalization, recency merge, provider selection,
retrieval, source classification, AnswerContract handoff, and persistence
packaging. Its Router/query-preparation responsibility is now mechanical:
collect already-computed facts, build/update the contract, and consume normalized
facts from that contract after each handoff.

## Behavior Preserved

AG-76D-RQ preserves:

- Router prompt text and retry prompt text;
- Researcher prompt text;
- Router JSON normalization semantics;
- entity fallback and retry behavior;
- nutrition/report-type override behavior;
- focus-academic and force-news override behavior;
- query generation inputs;
- query finalization, official-source bias insertion, and recency merge behavior;
- query text and order;
- provider override merge and provider selection semantics;
- search depth, retrieval budgets, ranking/filtering, and retrieval loop behavior;
- source-obligation bridge behavior;
- AnswerContract, Author, final answer, citation, DB/schema, JSONL/session,
  SQLite, and RunOutcome shapes.

## Tests Added / Updated

Added `tests/test_ag76d_rq_router_query_preparation_contract.py` covering:

1. Router JSON normalization parity.
2. Entity fallback and router retry parity/provenance.
3. Routing override merge parity and passive provenance capture.
4. Existing query text/order parity.
5. Official-source bias and recency-query merge parity.
6. Trace compatibility with additive contract visibility.
7. Static protected-import guard for the new contract module.
8. Orchestrator authority guard proving post-handoff consumption from the
   contract.
9. Protected-surface guard proving the contract does not call or import closed
   provider/depth/prompt/final-answer/citation/cache surfaces.
10. Offline fake-pipeline execution with no live provider/model/search calls.

## Trace Compatibility

Existing router/query trace fields remain present: `intent`, `query_type`,
`primary_entity`, `entities`, `router_entity_retry_used`,
`router_original_report_type`, `router_original_query_type`,
`routing_override_applied`, `routing_override_reason`, `report_type`,
`queries_per_iteration`, and `pass_providers`.

The only trace shape change is additive: `router_query_preparation_contract`, a
sanitized controller-owned visibility packet. It does not include raw prompts,
raw Router payloads, provider payloads, secrets, local DB rows, or output
packets.

## Protected Surfaces Kept Closed

AG-76D-RQ kept closed prompt text, Router/Researcher behavior, provider/model
configuration, provider routing/selection/depth, query-generation behavior,
query-finalization behavior, retrieval ranking/filtering, Author/final answer,
citation formatting/selection, Economist, Scrutineer, follow-up behavior,
weak/off-topic/failure-card behavior, DB schema, JSONL/session/SQLite/RunOutcome
shape, package/CLI/env compatibility names, LLM caching, and source-specific
hardcoding.

## Stop Conditions

Stop instead of extending this phase if parity requires prompt changes,
model/provider changes, query-generation/finalization behavior changes, provider
routing/depth changes, retrieval ranking/filtering changes, Author/citation/final
answer changes, DB/schema or RunOutcome shape changes, provider/model/search
calls from the contract, broad orchestrator rewrite, live validation, secrets,
raw prompts/payloads/traces, local DB rows, output packets, cache work, package
renames, or a product/design decision outside Router/QueryPreparation ownership.

## Recommended Next Phase

Recommended next phase: **AG-76D-RL — Controller-Owned Retrieval Loop Contract**.

Rationale: AG-76D-RQ makes Router/query-preparation posture controller-visible
and contract-owned, but the broader retrieval execution/continuation/provider
loop still contains local orchestration authority beyond the already-transferred
retrieval stop/continue decision. That is the next coherent AG-76D core
authority-transfer seam.
