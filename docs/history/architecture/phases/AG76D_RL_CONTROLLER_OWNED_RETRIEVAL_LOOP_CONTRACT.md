Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG76D_RL_CONTROLLER_OWNED_RETRIEVAL_LOOP_CONTRACT).

# AG-76D-RL Controller-Owned Retrieval Loop Contract

Date: 2026-05-31

Phase type: **core authority transfer**

Mode: Architecture Groove / Prove Mode

## Licensed Protected Surface

AG-76D-RL opens only the broader retrieval-loop contract/state seam: retrieval
pass descriptors, a passive execution envelope, a mechanical runner/handoff
adapter, pass-result summaries, and additive trace/controller visibility fields
proving Controller-owned retrieval-loop authority.

The phase does **not** license provider routing changes, provider selection
changes, provider depth changes, query generation or finalization changes,
prompt/model behavior changes, retrieval ranking/filtering changes,
source-class classifier/currentness changes, candidate-fit changes,
weak-corpus/failure-card behavior changes, Author/citation/final-answer changes,
Economist/Scrutineer/follow-up behavior changes, DB/session/RunOutcome shape
changes, package/CLI/env renames, cache implementation, live validation, or real
provider/model/search calls.

## Retrieval-Loop Decisions Still Orchestrator-Owned After RL-SC and RQ

After AG-76D-RL-SC and AG-76D-RQ, stop/continue authority had moved to
`RetrievalStopDecision`, and router/query-preparation posture had moved to
`RouterQueryPreparationState`. The following retrieval-loop facts still lived as
orchestrator-local loop state:

1. Per-pass retrieval descriptors: iteration, query source, active queries,
   provider list, search depth, provider role, similarity basis, and retrieval
   budget facts.
2. Per-pass execution envelope: include/exclude domains, academic domain filter,
   entity hint, and the existing search executor call boundary.
3. Provider/search allocation facts after the existing selectors had already
   produced provider lists and search depth.
4. Batch-dispatch authorization references, source-class lifecycle references,
   weak-corpus references, and RetrievalStopDecision references as opaque
   already-computed facts.
5. Pass result summaries after search completed: query/provider counts, result
   count, and seen-url delta.
6. Trace evidence proving that the runner did not generate queries, select
   providers, choose depth, rank/filter sources, or change prompt/final-answer
   behavior.

## New Controller-Owned Retrieval Loop Contract / State

`core.retrieval_loop_contract` adds the passive Controller-owned retrieval-loop
contract:

- `RetrievalPassDescriptor` records one already-authorized retrieval pass.
- `RetrievalExecutionEnvelope` records the mechanical execution envelope around
  that descriptor.
- `RetrievalPassResultSummary` records sanitized pass-completion facts after the
  existing search executor returns.
- `RetrievalLoopState` exposes a sanitized `retrieval_loop_contract` trace packet
  and matching controller-state payload.
- Builder functions copy already-computed facts into the contract without
  calling providers, models, prompts, search, ranking/filtering, Author,
  citation, persistence, or final-answer code.

The schema is `ag76d_rl_v1`; every trace packet is explicitly marked
`controller_owned: true`.

## Retrieval Pass / Action Descriptor

The pass descriptor records:

- iteration identity;
- query source;
- current queries in order;
- already-selected provider list;
- already-selected search depth;
- results-per-query, top-chunks, and max-iterations budget facts;
- intent and complexity;
- provider role;
- similarity prior/query-basis facts;
- retrieval budget facts;
- batch-dispatch authorization, source-class recovery, and weak-corpus recovery
  references as opaque already-computed facts.

It is a descriptor only. It does not generate queries, select providers, choose
depth, dispatch search, rank/filter sources, or change final-answer behavior.

## Mechanical Runner / Handoff Boundary

`execute_retrieval_pass_handoff(...)` is the production-active mechanical runner
adapter. It consumes a `RetrievalExecutionEnvelope` and calls the existing
`process_search_queries` dependency with the descriptor's queries, intent,
complexity, depth, results-per-query, and provider list.

The runner boundary is deliberately narrow:

- provider selection remains the existing precomputed value;
- search depth remains the existing precomputed value;
- query order remains the existing precomputed value;
- include/exclude domains, entity hint, academic filter, embeddings, seen URLs,
  image collection, diagnostics, and similarity facts remain existing mechanical
  executor inputs;
- no provider/model/search implementation changes were made.

## Relationship to RetrievalStopDecision

AG-76D-RL preserves `RetrievalStopDecision` as the active stop/continue owner.
The retrieval-loop contract only stores a `retrieval_stop_decision_ref` for
visibility. It does not reimplement stop/continue authority, redundancy checks,
budget exhaustion checks, sufficiency checks, or weak-corpus completion checks.

## Relationship to RouterQueryPreparationState

`RouterQueryPreparationState` feeds the retrieval-loop contract when available:

- finalized queries and current queries are copied from its
  `query_text_order_facts`;
- query source is copied from its `query_preparation_provenance`;
- router/query-preparation schema and controller-owned flags are exposed as an
  upstream reference.

The retrieval-loop contract does not replace RQ. It starts from the RQ handoff
and records broader retrieval-loop execution posture.

## Behavior Preserved

AG-76D-RL preserves:

- provider list and provider selection behavior;
- provider override/merge behavior;
- search depth behavior;
- query strings and query order;
- results-per-query, top-chunks, and max-iterations budgets;
- retrieval batch-dispatch semantics;
- RetrievalStopDecision stop/continue ownership;
- RouterQueryPreparationState router/query-preparation ownership;
- search executor dependency and fake/offline test harness behavior;
- ranking/filtering, source-class recovery, weak-corpus, conflict-resolution,
  Analyst, Author, citation, final-answer, Economist, Scrutineer, follow-up,
  persistence, DB/session, and RunOutcome behavior.

Runtime behavior changes are expected to be none except authority ownership and
additive trace/controller visibility.

## Production-Active vs Shadow-Only Paths

Production-active:

- `RetrievalPassDescriptor` construction for the main retrieval pass;
- `RetrievalExecutionEnvelope` construction for the main retrieval pass;
- `execute_retrieval_pass_handoff(...)` as the mechanical adapter around the
  existing `process_search_queries` dependency;
- `RetrievalLoopState` trace/controller-state visibility for the latest main
  retrieval pass;
- `RetrievalPassResultSummary` for completed main retrieval pass results.

Shadow-only: none introduced for AG-76D-RL.

Test-only:

- offline fake-loop parity tests in
  `tests/test_ag76d_rl_controller_owned_retrieval_loop_contract.py`.

Inactive replacement infrastructure: none.

## Tests Added / Updated

Added `tests/test_ag76d_rl_controller_owned_retrieval_loop_contract.py`, covering:

1. Controller ownership of the state, descriptor, and execution envelope.
2. Provider/depth/query/results/top-chunks/max-iterations parity.
3. Mechanical runner/handoff behavior using a fake search executor.
4. RetrievalStopDecision ownership.
5. RouterQueryPreparationState feed into the retrieval-loop contract.
6. Additive pass-result summary visibility.
7. Static orchestrator guard for descriptor/state/handoff use at the scoped seam.
8. Protected-surface guard proving the contract module does not open prompt,
   Author, citation, persistence, provider, or live network surfaces.
9. Trace compatibility guard preserving existing retrieval/provider/query fields.
10. Offline fake-loop parity for first and continuation passes.

## Trace Compatibility and Additive Visibility

Existing trace fields remain present, including `pass_providers`,
`queries_per_iteration`, retrieval stop telemetry, retrieval batch dispatch trace,
provider diagnostics, and `router_query_preparation_contract`.

AG-76D-RL adds one sanitized trace packet: `retrieval_loop_contract`. It contains
controller-owned descriptors, envelope metadata, retrieval budget facts,
RetrievalStopDecision and RouterQueryPreparation references, pass-result
summaries, and explicit booleans proving the contract did not generate queries,
select providers, choose depth, rank/filter sources, or change prompt/final
answer behavior.

The packet does not include raw prompts, raw provider payloads, secrets, local DB
rows, local output packets, or raw full traces.

## Protected Surfaces Kept Closed

Kept closed:

- provider routing/selection/depth changes;
- new providers/provider swaps;
- query generation/finalization changes;
- prompt text/model-call behavior;
- real provider/model/search calls;
- retrieval ranking/filtering;
- source-class classifier/currentness and candidate-fit semantics;
- weak-corpus/failure-card behavior;
- Analyst/Author/citation/final-answer behavior;
- Economist, Scrutineer, and follow-up behavior;
- DB/session/RunOutcome shape;
- package/CLI/env/session/database compatibility names;
- LLM workflow cache implementation;
- live validation.

## Stop Conditions

Stop AG-76D-RL instead of continuing if the contract would need to change
provider routing, provider selection, provider depth, query generation,
query-finalization, prompt/model behavior, ranking/filtering, final-answer or
citation behavior, weak-corpus/failure-card behavior, source-class currentness,
candidate-fit semantics, persistence shapes, package/CLI/env compatibility, or
if the contract would need to execute providers/search directly rather than
describe and hand off already-computed pass facts.

## Recommended Next Phase

Recommended next core authority transfer: **AG-76D-WG — Controller-Owned Weak /
Off-topic / Failure-card Gate Contract**.

Rationale: AG-76D-RL now makes broader retrieval-loop pass authority
Controller-visible while preserving behavior. The next highest authority risk is
weak/off-topic/failure-card gating, because those branches can still influence
recovery, displayability, and failure posture from orchestrator-local state.
