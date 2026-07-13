Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG90J_RETRIEVAL_STOP_CONTINUATION_TRACE_PROJECTION).

# AG-90J Retrieval-Stop / Continuation Trace Projection Burn-Down

## Inspected block

The inspected production surfaces were the AG-90I safe burn-down candidates in
`core/pipeline_orchestrator.py`:

- module-level retrieval-stop default, shadow telemetry, active decision
  serialization, and active/shadow alignment helpers;
- the local retrieval-stop shadow-recording and ordinary-continuation candidate
  packaging glue inside `_run_pipeline_inner(...)`;
- the post-retrieval ordinary-continuation trace projection adapter that only
  repackages already-computed runtime facts.

No live provider, model, search, or validation calls were run for this phase.

## Selected extraction

`core/retrieval_stop_trace_projection.py` now owns deterministic projection-only
packaging for:

- retrieval-stop shadow defaults and shadow telemetry serialization;
- retrieval-stop active defaults and terminal active stop telemetry
  serialization for no-query and budget-exhausted branches;
- active/shadow alignment telemetry projection;
- retrieval-stop shadow-recording trace projection plus ordinary-continuation
  candidate packaging for the local retrieval loop seam;
- ordinary-continuation candidate trace projection from existing runtime facts.

The orchestrator still owns retrieval loop execution and still calls the
existing controller-owned stop/continue decision boundary. The helper packages
facts after those decisions and does not choose whether to stop, continue,
retry, recover, expand, scout, or search.

## Size accounting

- `core/pipeline_orchestrator.py` before: 5,590 lines.
- `core/pipeline_orchestrator.py` after: 5,252 lines.
- Orchestrator reduction: -338 lines.
- Helper line count: 334 lines.
- Production-code delta: +368 / -372, net -4 lines.
- Total repo delta: +768 / -380, net +388 lines including focused parity tests, static-guard updates, and this architecture note.

## Exact projection surface moved

Moved projection surfaces are limited to JSON-safe dict/default/trace packaging
for already-computed retrieval-stop and ordinary-continuation facts:

- shadow defaults and active defaults;
- shadow controller telemetry serialization;
- active terminal stop telemetry serialization;
- active/shadow alignment string projection;
- local shadow telemetry plus ordinary-continuation candidate trace packaging;
- ordinary-continuation candidate trace repackaging from existing candidate and
  evidence-state facts.

## Authority owner preserved

Stop/continue authority remains with `core.retrieval_stop_controller` and the
existing orchestrator callsites that invoke it. The helper imports the
retrieval-stop controller only to use the existing controller-owned input and
decision APIs for the same deterministic telemetry serialization that already
existed in the orchestrator.

## Protected surfaces kept closed

This extraction did not move or change:

- retrieval loop execution;
- query generation, mutation, text, order, or `QueryPlan` authority;
- provider routing or selection;
- provider/model/search callsites;
- search-depth policy;
- retrieval ranking/filtering;
- source satisfaction behavior;
- final evidence selection;
- citation formatting;
- Author behavior;
- persistence, DB, cache, or session side effects.

## Parity and static seam proof

`tests/test_ag90j_retrieval_stop_trace_projection.py` covers exact dict parity
for active stop telemetry, continue trace projection, no-query stop telemetry,
budget-exhausted active telemetry, shadow-only defaults, active/shadow alignment,
and ordinary-continuation trace projection. It also statically guards the helper
against forbidden provider/search/model/prompt/citation/final-evidence,
persistence, DB, cache, raw-scope, `globals()`, and `locals()` seams.

Existing retrieval-stop and retrieval-loop tests remain the runtime parity check
that the orchestrator wiring did not alter retrieval behavior.

## Remaining candidates

Potential future deterministic candidates remain in the broader lifecycle trace
projection area identified by AG-90I, especially weak-corpus, conflict,
targeted-retrieval, and evidence-integration lifecycle fact serialization. They
should be split into bounded projection-only slices and must not collapse source
satisfaction, query, provider, search-depth, final-evidence, citation, Author,
or persistence authority.
