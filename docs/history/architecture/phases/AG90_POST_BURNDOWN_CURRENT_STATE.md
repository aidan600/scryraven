Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG90_POST_BURNDOWN_CURRENT_STATE).

# AG-90 Post-Burndown Current State

## Scope

This note is the post-AG-89 / post-AG-90 current-state baseline for the
orchestrator burn-down sequence. It is intentionally docs-only. It does not
license runtime behavior changes, live validation, provider/model/search calls,
or new wrapper surfaces.

## Current line count

- `core/pipeline_orchestrator.py`: **5,069** lines.
- Public compatibility entry point: `run_pipeline(...)` remains in the
  orchestrator.
- Monolithic runtime body: `_run_pipeline_inner(...)` remains in the
  orchestrator.

## Post-AG-89 authority baseline

AG-89 established that several major authority surfaces are no longer supposed
to be re-decided by the orchestrator or by trace wrappers:

- `OfficialCurrentSourceCustodyState` owns official/current custody state.
- `QueryPlan` owns planned query text, query ordering, and query-plan authority.
- `FinalAnswerPacket` owns final-answer packet authority and packet-derived
  Author/citation handoff facts.
- Trace-only wrappers should collapse into deterministic projections rather than
  becoming hidden policy engines.

The AG-90 extractions below should be read against that authority baseline:
helpers may package, project, or execute an explicitly scoped runtime step, but
must not re-own the AG-89 authority surfaces.

## Extracted helpers and responsibility classification

| Phase | Helper | Responsibility | Classification |
|---|---|---|---|
| AG-90A | `core/session_output_projection.py` | Builds legacy execution-trace and execution-log/session-output projection shapes from already-computed runtime values. | Projection helper; not an authority owner. |
| AG-90B | `core/final_answer_runtime_assembly.py` | Assembles pre-Author `FinalAnswerPacket`/Author payload facts and post-Author citation/runtime handoff facts from scoped inputs. | Authority adapter to `FinalAnswerPacket`; helper must stay subordinate to packet authority. |
| AG-90C | `core/runtime_prompt_assembly.py` | Builds deterministic prompt strings/fragments for Analyst, Expander, Economist preflight, Scrutineer, unsupported-retrieval messaging, Author image context, Author prompt, and Author system-key selection. | Prompt assembly helper; protected product surface, not a new prompt-policy authority. |
| AG-90D | `core/retrieval_dispatch_runtime.py` | Packages and executes recorded retrieval dispatches, main retrieval pass dispatch, disambiguation retry dispatch, supplemental/Scrutineer remediation dispatch, source-class recovery context, and conflict-resolution dispatch. | Execution helper; not provider/query/search-depth authority. |
| AG-90E | `core/legacy_review_runtime_stage.py` | Encapsulates legacy synthesis-evaluator and Scrutineer runtime execution/re-run plumbing. | Runtime execution helper; not review-policy authority. |
| AG-90F | `core/analyst_runtime_stage.py` | Encapsulates pre-Analyst gate, post-Economist Analyst gate, Analyst model-call recorder, and Analyst runtime execution. | Runtime execution helper with gate-adapter functions; not final evidence or Author authority. |
| AG-90G | `core/post_analyst_handoff_packaging.py` | Packages Analyst-to-Author/Economist handoff telemetry, quantitative source telemetry, and Economist-skip shadow facts. | Projection/handoff helper; not Economist or Author authority. |
| AG-90H | `core/post_author_output_projection.py` | Packages post-Author trace fragments, final output metadata, final runtime trace/output projection, execution-log inputs, and `RunOutcome` construction. | Projection/output helper; not final-answer, citation, persistence, or Author authority. |
| AG-90J | `core/retrieval_stop_trace_projection.py` | Projects retrieval-stop shadow/active telemetry, active-shadow alignment, terminal stop trace fields, and ordinary-continuation trace facts from existing controller/runtime decisions. | Projection helper subordinate to `core/retrieval_stop_controller`; stop/continue authority remains with the controller. |
| AG-90K | `core/lifecycle_trace_projection.py` | Serializes weak-corpus lifecycle facts, conflict-resolution lifecycle facts, and the compact evidence-integration snapshot from already-computed runtime/controller facts. | Projection helper subordinate to weak-corpus, conflict-resolution, evidence-integration, and controller-loop authorities. |

## Authority owners vs. projection/execution helpers

### Authority owners preserved

- `core/query_plan.py` and `core/query_plan_runtime_adapter.py` retain query-plan
  authority and query-plan runtime posture.
- `core/official_current_source_custody.py` retains official/current custody
  authority.
- `core/final_answer_packet.py` retains final-answer packet authority.
- `core/retrieval_stop_controller.py` retains stop/continue authority.
- `core/weak_corpus_controller.py` retains weak-corpus recovery authority.
- `core/conflict_resolution_controller.py` retains conflict-resolution decision
  authority.
- `core/evidence_integration_checkpoint.py` retains evidence-integration
  checkpoint authority.
- `core/controller_loop_spine.py` retains controller-loop dispatch authority.
- Existing provider routing/search-depth/query-generation code remains protected
  behavior unless a later product or authority phase explicitly takes it on.

### Projection/execution helpers, not authority owners

- `session_output_projection`, `post_author_output_projection`,
  `retrieval_stop_trace_projection`, and `lifecycle_trace_projection` should
  remain deterministic serializers of already-computed facts.
- `runtime_prompt_assembly` should remain deterministic prompt assembly from
  explicit inputs; it must not become a hidden prompt-policy owner.
- `retrieval_dispatch_runtime`, `legacy_review_runtime_stage`, and
  `analyst_runtime_stage` may execute explicitly scoped runtime steps, but they
  must not select new provider/query/search-depth/final-answer policy.
- `post_analyst_handoff_packaging` should remain handoff/telemetry packaging.
- `final_answer_runtime_assembly` may adapt scoped runtime values into
  `FinalAnswerPacket` and citation handoff flows, but the packet remains the
  authority.

## Remaining orchestrator responsibilities

`core/pipeline_orchestrator.py` still owns the compatibility shell and the
end-to-end sequencing of the runtime pass. In current form it still performs or
hosts:

- dependency extraction from `RunDeps`, status reporting, run/session setup, and
  compatibility entry-point behavior;
- pre-retrieval routing, entity extraction, session-title generation, scout/recon
  setup, and query/depth/provider preparation;
- retrieval loop sequencing, including when to call retrieval dispatch helpers
  and controller/recovery helpers;
- live callsite ownership for remaining model/search/embedding/retrieval
  interactions;
- lifecycle integration across source-class recovery, weak-corpus recovery,
  conflict resolution, targeted retrieval, retrieval-stop, and evidence
  integration;
- final evidence bundle call orchestration;
- Author model-call orchestration;
- final session payload construction and persistence side-effect execution;
- compatibility aliases for extracted helper functions that older tests or
  callers still inspect.

## Remaining protected behavior surfaces

The following surfaces remain closed to docs-only or projection-only phases:

- provider routing, provider selection, provider overrides, and search provider
  allocation;
- search-depth selection and supplemental depth behavior;
- query generation, query mutation, query order, and `QueryPlan` authority;
- retrieval loop execution, provider result handling, ranking, filtering, and
  useful-content decisions;
- official/current source custody and source-satisfaction semantics;
- targeted-retrieval currentness/source-fit interpretation;
- weak-corpus recovery approval behavior;
- conflict-resolution retrieval behavior;
- final evidence selection and final evidence bundle semantics;
- citation eligibility, citation formatting, and source presentation;
- Author prompt/product behavior, Author model-call behavior, and final prose;
- persistence, DB/cache/session writes, and execution-log side effects;
- any live provider/model/search validation.

## Remaining safe burn-down candidates

Safe candidates are limited to deterministic projection slices that serialize
already-computed facts and can be parity-tested without live calls:

1. **Targeted split of remaining lifecycle trace serialization.** The AG-90K
   note deliberately left targeted-retrieval currentness/source-fit projection in
   the orchestrator because it still interprets source-fit/currentness facts.
   A safe follow-up may only move raw serialization once the authority boundary
   is explicit and guarded.
2. **Compatibility alias cleanup.** Remove or demote stale compatibility aliases
   only after static consumer inventory proves they are unused or covered by a
   stable facade.
3. **Final output/session projection thinning.** Additional packaging around
   already-computed session/output facts may be safe if it does not touch
   persistence execution or `FinalAnswerPacket` semantics.
4. **Trace attachment grouping.** Remaining trace-key assembly can move only as
   exact dict/list projection with static guards against provider/model/search,
   prompt, citation, evidence-selection, and persistence seams.

## Remaining authority/product candidates

These are not safe projection burn-down items. They need explicit authority or
product acceptance because they can change behavior quality:

- pre-retrieval query/depth/provider authority mapping;
- provider allocation and search-depth policy;
- scout/recon behavior and source-acquisition quality;
- targeted-retrieval source-fit/currentness interpretation;
- official/current acquisition and custody quality;
- Project Source retrieval integration;
- cache policy and cache-hit behavior;
- Evidence Health / evidence-quality product lanes;
- final evidence selection, citation posture, and Author presentation quality.

## Stop/pause recommendation

Recommendation: **pause AG-90 as an orchestrator burn-down lane unless the next
slice is a very small deterministic projection-only cleanup.** The remaining
large surfaces are increasingly authority/product surfaces rather than safe
trace-wrapper collapse.

Explicit next-phase options:

1. **Safe deterministic projection burn-down.** Continue only with a bounded
   trace/session/lifecycle projection slice, exact fixture parity, and static
   guards proving no provider/model/search/prompt/citation/final-evidence or
   persistence authority moved.
2. **Pre-retrieval query/depth/provider authority map.** Start a dedicated
   authority audit before moving query/depth/provider behavior. The goal should
   be to map owners and protected seams, not to thin code opportunistically.
3. **Pause AG-90 and switch to product lanes.** Prefer cache, Project Source
   retrieval, Evidence Health, or official/current acquisition if the desired
   next work is product value rather than deterministic orchestrator thinning.

## Baseline checks for this note

This current-state baseline was prepared from static repository inspection. It
requires only docs sanity and import/compile checks; it does not require or
permit live ScryRaven, proplex, provider, model, or search calls.
