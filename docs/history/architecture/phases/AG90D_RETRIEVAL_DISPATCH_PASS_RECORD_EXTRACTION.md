Status: historical
Authority: none
Default-read: no
Historical-scope: Historical architecture phase/proof record (AG90D_RETRIEVAL_DISPATCH_PASS_RECORD_EXTRACTION).

# AG-90D Retrieval Dispatch / Pass-Record Runtime Seam Extraction

## Phase

AG-90D is a behavior-preserving subtractive extraction from `core/pipeline_orchestrator.py`. It moves repeated retrieval dispatch plumbing and retrieval pass-record assembly into a bounded mechanical helper without changing provider routing, query authority, search-depth policy, prompt text, model calls, source ranking/filtering, citation formatting, or final-answer behavior.

## Retrieval callsites inspected

| Callsite | Previous owner | Classification | Extraction decision | Risk / notes |
| --- | --- | --- | --- | --- |
| Main loop retrieval handoff around `execute_retrieval_pass_handoff(...)` | `pipeline_orchestrator.py` | Main retrieval / weak-corpus recovery role | Extracted to `execute_main_retrieval_pass_from_scope(...)` and `execute_main_retrieval_pass_runtime(...)` | Low-medium risk because it also carries Controller retrieval-loop telemetry; preserved descriptor/envelope construction, previous pass summaries, exact handoff dependency mapping, pass record, URL delta, and chunk delta. |
| Disambiguation retry `process_search_queries(...)` | `pipeline_orchestrator.py` | Retry / disambiguation | Extracted to `execute_disambiguation_retry_from_scope(...)` via `execute_recorded_retrieval_dispatch(...)` | Low risk; query generation/finalization and retry decision remain in the orchestrator/QueryPlan authority. Helper only receives finalized `rqs`, selected providers, depth, and role. |
| Synthesis evaluator supplemental-search `process_search_queries(...)` | `pipeline_orchestrator.py` | Supplemental search | Extracted to `execute_supplemental_search_from_scope(...)` | Low risk; deficiency detection, supplemental query generation, supplemental depth choice, and provider selection remain outside the helper. Helper returns passages and URL delta only. |
| Scrutineer remediation `process_search_queries(...)` | `pipeline_orchestrator.py` | Remediation | Extracted to `execute_scrutineer_remediation_from_scope(...)` | Low risk; Scrutineer JSON/model call, novelty filtering, provider selection, and linkup depth override authorization remain in the orchestrator. Helper receives the already-authorized override value. |
| Source-class recovery runner context | `pipeline_orchestrator.py` | Recovery dispatch context | Extracted to `source_class_recovery_context_from_scope(...)` | Medium risk because it has many shared retrieval dependencies; helper uses a strict whitelist from scope and preserves search providers, Exa domain filter, entity hint, diagnostics, and pass-record list references. |
| Conflict-resolution recovery dispatch arguments | `pipeline_orchestrator.py` | Recovery / conflict resolution | Extracted to `execute_conflict_resolution_from_scope(...)` | Medium risk because the executor owns conflict semantics; helper only forwards the existing decision and exact retrieval dependencies to the existing executor. |

No scout/continuation direct `process_search_queries(...)` callsite remained in the orchestrator after AG-90C-era extractions; continuation recovery still flows through existing recovery/runner modules.

## Selected extraction

Introduced `core/retrieval_dispatch_runtime.py` as the bounded mechanical runtime seam for already-authorized retrieval execution. The helper module owns:

* `RetrievalDispatchDeps` — a dependency bundle for the existing search executor and caller-owned mutable collections.
* `RecordedRetrievalDispatch` — already-authorized retrieval facts: stage, queries, providers, provider role, search depth, results per query, optional Exa filter, optional Linkup depth override, entity hint, iteration, and similarity metadata.
* `build_retrieval_pass_record(...)` — construction of the existing pass-record dictionary shape.
* `execute_recorded_retrieval_dispatch(...)` — exact delegation to injected `process_search_queries(...)`, pass-record assembly, URL delta calculation, and chunk delta calculation.
* `execute_main_retrieval_pass_runtime(...)` — main-pass descriptor/envelope/Controller loop-state assembly plus existing retrieval handoff execution.
* Strict-whitelist scope wrappers for orchestrator callsites where passing every already-existing local individually would reintroduce the line-heavy plumbing the phase is meant to retire.

## Before/after line counts

* Before: `core/pipeline_orchestrator.py` had **7,122** lines at phase start.
* After: `core/pipeline_orchestrator.py` has **6,920** lines.
* Net delta: **-202 lines**.

## Surfaces moved out of orchestrator

Moved out of the orchestrator:

* Main retrieval descriptor/envelope construction and retrieval-loop pass-result summary wiring.
* Main retrieval pass-record append for the existing `retrieval_pass_records` shape.
* Disambiguation retry dispatch call, pass-record append, URL delta, and chunk delta bookkeeping.
* Supplemental-search dispatch call and URL delta bookkeeping.
* Scrutineer remediation dispatch call.
* Source-class recovery retrieval runner context assembly.
* Conflict-resolution retrieval executor argument fan-out.

## Helper responsibilities

The helper may:

* call an injected `process_search_queries(...)` with already-selected providers, already-authorized queries, caller-provided depth, caller-provided result count, and existing retrieval dependency objects;
* build the existing retrieval pass-record dictionary shape;
* append pass records when the previous callsite appended them;
* compute URL/chunk deltas from caller-owned collections;
* build main-pass retrieval loop descriptor/envelope telemetry using facts supplied by the orchestrator.

The helper must not and does not:

* import or call provider-selection logic such as `select_providers`;
* choose search depth or result count;
* generate, mutate, reorder, classify, or filter queries;
* rank/filter retrieved passages;
* import prompt modules;
* call `ask_model` or any model interface;
* decide whether retrieval should happen.

## Exact dispatch / parity proof

Focused AG-90D tests prove that:

* representative pass records preserve `stage`, `iteration`, `queries`, `providers`, `provider_role`, `search_depth`, and `results_per_query` fields;
* `execute_recorded_retrieval_dispatch(...)` delegates to an injected fake `process_search_queries` with the same positional argument ordering and keyword mapping used by the previous orchestrator callsites;
* caller-owned `seen_urls` and `collected_images` collections are forwarded by identity rather than replaced;
* URL/chunk deltas are reported from side effects without mutating query lists;
* static guards keep provider selection, prompt/model imports, and search-depth policy outside `core/retrieval_dispatch_runtime.py`;
* static guards verify direct orchestrator `process_search_queries(` callsites were moved to the helper and that the orchestrator line count meets the AG-90D minimum.

## Protected surfaces kept closed

Kept closed and unchanged:

* QueryPlan authority and query text/order finalization.
* Provider routing and provider selection.
* Search-depth policy and supplemental depth choice.
* Provider/model/search integration behavior.
* Query generation quality.
* Retrieval ranking/filtering and evidence selection.
* Official/current custody behavior.
* Prompt text and prompt assembly.
* Model calls and author prose behavior.
* Citation formatting and FinalAnswerPacket authority semantics.
* Cache reuse and persistence behavior.

## Remaining high-value extraction candidates

* The retrieval-loop pre/post decision spine around stop/continue telemetry remains line-heavy and could move into a Controller-owned loop-runtime adapter once authority boundaries are fully explicit.
* Source-class recovery and conflict-resolution dispatch contexts now have scope wrappers, but their underlying executor modules still carry repeated dependency lists that could be normalized around a shared retrieval dependency object.
* Provider-selection callsites remain in the orchestrator by design for AG-90D; a future phase could inventory them without moving authority.
* Final evidence bundle rebuilds after supplemental/remediation retrieval remain local because AG-90D did not license evidence-selection behavior changes.

## Recommended next phase

Recommended next phase: extract a small retrieval-loop telemetry reducer that consumes already-computed Controller decisions and retrieval outcomes, while still leaving provider selection, query authority, search depth, prompt construction, and model calls in their current owners.
