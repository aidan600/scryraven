Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG90K_LIFECYCLE_FACT_PROJECTION_SLICE).

# AG-90K — Lifecycle Fact Projection Slice

## Scope inspected

AG-90K inspected the AG-90I lifecycle projection area in
`core/pipeline_orchestrator.py`, specifically the weak-corpus lifecycle fact
serializer, conflict-resolution lifecycle fact serializer, and the compact
AG-32 evidence-integration snapshot builder. Targeted-retrieval currentness and
source-fit projection stayed in the orchestrator because that surface still
interprets source-fit/currentness facts and belongs in a separate authority or
product phase.

## Selected extraction

The deterministic projection-only helper `core/lifecycle_trace_projection.py`
now owns only serialization of already-computed runtime facts:

- `weak_corpus_lifecycle_facts(...)`
- `conflict_resolution_lifecycle_facts(...)`
- `build_evidence_integration_snapshot_from_runtime(...)`

The helper does not decide whether weak-corpus recovery, conflict resolution,
targeted retrieval, continuation, or evidence integration should happen. Existing
controller/recovery decisions remain the authority owners; the helper only
projects their outputs into the same trace/snapshot shapes the orchestrator
previously built inline.

## Line counts and deltas

- `core/pipeline_orchestrator.py` before: **5,252** lines.
- `core/pipeline_orchestrator.py` after: **5,069** lines.
- Orchestrator line-count reduction: **183** lines.
- Helper line count: **175** lines.
- Production-code delta: **-8** lines (`pipeline_orchestrator.py` -183 plus
  `lifecycle_trace_projection.py` +175).
- Total repo delta at implementation time: tests and this note add non-production
  coverage/documentation on top of the negative production-code delta.

## Exact projection surface moved

- Weak-corpus lifecycle fact dicts for approved, skipped, and absent decisions.
- Conflict-resolution lifecycle fact dicts for approved controller decisions and
  lifecycle-only fallback when no controller decision exists.
- Evidence-integration AG-32 snapshot assembly from already-computed answer
  contract, source-class lifecycle, weak-corpus, retrieval-stop shadow, and
  runtime budget facts.

## Authority owner preserved

- Weak-corpus recovery authority remains in `core/weak_corpus_controller.py` and
  the orchestrator call sites that decide when to ask or consume it.
- Conflict-resolution authority remains in
  `core/conflict_resolution_controller.py` and the existing orchestrator runtime
  lifecycle builder.
- Evidence-integration checkpoint authority remains in
  `core/evidence_integration_checkpoint.py`.
- Controller-loop dispatch authority remains in `core/controller_loop_spine.py`.

## Protected surfaces kept closed

AG-90K did not move or alter:

- weak-corpus recovery behavior;
- conflict-resolution retrieval behavior;
- query generation, mutation, or ordering;
- QueryPlan authority behavior;
- provider routing or selection;
- search-depth policy;
- retrieval loop execution;
- retrieval ranking or filtering;
- source satisfaction behavior;
- final evidence selection;
- citation formatting;
- Author behavior;
- persistence side effects;
- live provider, model, or search calls.

## Static seam guard

Focused AG-90K tests assert that `core/lifecycle_trace_projection.py` does not
import provider/search/model/prompt/citation/final-evidence/persistence/cache
surfaces, does not call known live/provider/model/search/persistence/final-answer
helpers, does not use `globals()` or `locals()`, and does not serialize a raw
scope object.

## Remaining candidates

- Targeted-retrieval currentness/source-fit projection remains a separate
  authority/product slice candidate.
- Broader pre-retrieval query/depth/provider surfaces remain closed until a
  dedicated authority/product phase.
