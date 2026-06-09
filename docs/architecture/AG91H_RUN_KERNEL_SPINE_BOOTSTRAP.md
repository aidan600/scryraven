# AG-91H RunKernel Spine Bootstrap

Status: implementation complete; behavior-preserving; no live validation.

## Purpose

AG-91H creates the first runtime-consumed RunKernel / RunAuthority spine for
ScryRaven. The goal is not a new orchestrator. The goal is a small canonical
RunState that issues actions before migrated stages execute, requires bounded
executors/adapters to consume those actions, reduces observations after
execution, and projects trace from RunState.

## Runtime Model

`core.run_kernel` owns:

- `RunState`: run/request identity, issued actions, reduced observations,
  action/stage statuses, compact state projections, and sequencing.
- `AuthorizedAction`: `action_id`, `run_id`, `stage`, `action_type`, `reason`,
  `inputs`, `expected_observation_type`, and sequence.
- `Observation`: `observation_id`, `run_id`, `action_id`, `stage`,
  `observation_type`, `status`, compact payload/projection, and sequence.
- `KernelTraceProjection`: a trace fragment derived from RunState.

The reducer rejects unmatched actions, wrong action IDs, wrong stages, wrong
observation types, out-of-order observations, and duplicate reductions. Payloads
are JSON-safe and redact sensitive keys such as raw prompts, provider payloads,
secrets, logs, caches, DB rows, and output packets.

## Wired Stages

### Route Request

Old owner: `pipeline_orchestrator.py` inline router prompt/model call.

New path: `RunKernel.authorize_route_request(...)` emits
`ActionType.ROUTE_REQUEST`. `core.routing_runtime.execute_route_request_action`
requires that action, preserves the existing router and retry prompt bytes/call
shape, returns the existing `RouterQueryPreparationState`, and emits
`ObservationType.ROUTE_RESULT`.

Runtime consumer proof: `pipeline_orchestrator.py` calls the router adapter only
after authorization and reduces `route_result.observation` before reading route
fields.

### QueryPlan Admission Boundary

Old owner: `pipeline_orchestrator.py` accepted recon/researcher candidate lists
directly into QueryPlan.

New path: `RunKernel.authorize_query_plan_admission(...)` emits
`ActionType.QUERY_PLAN_ADMISSION`. `core.query_production_runtime.
execute_query_plan_admission_action` requires that action, admits existing
candidates into QueryPlan, applies the existing QueryPlan recency/finalization
boundary, updates router runtime posture, and emits
`ObservationType.QUERY_PLAN_ADMITTED`.

QueryPlan remains the owner of query identity and order. RunState stores the
QueryPlan projection/reference; it does not refinalize or reorder queries.

### Main Retrieval Scheduling / Dispatch

Old owner: `pipeline_orchestrator.py` scheduled the main pass directly from
compatibility locals.

New path: `RunKernel.authorize_main_retrieval_pass(...)` emits
`ActionType.MAIN_RETRIEVAL_PASS`. `RetrievalScheduler` remains the scheduler
authority through `schedule_main_retrieval_from_kernel_action(...)`, which
validates the kernel action before delegating to existing scheduler logic.
`execute_main_retrieval_pass_from_scope(...)` now requires the same kernel
action plus the existing `RetrievalScheduledAction`, executes the unchanged
mechanical dispatch path, and emits `ObservationType.RETRIEVAL_PASS_RESULT`.

Provider/depth/query behavior remains delegated to ProviderPlan, QueryPlan, and
RetrievalScheduler.

### Retrieval Stop / Continue Checkpoint

Old owner: direct orchestrator calls into `decide_retrieval_stop(...)`.

New path: `RunKernel.authorize_retrieval_stop_checkpoint(...)` emits
`ActionType.RETRIEVAL_STOP_CHECKPOINT`. `decide_retrieval_stop_with_kernel_action`
requires that action, calls the existing stop controller without changing stop
policy, and emits `ObservationType.RETRIEVAL_STOP_DECISION`.

RunState records the stop/continue decision projection and next-stage readiness
while `retrieval_stop_controller` remains the policy owner for this phase.

## Retained Compatibility

`pipeline_orchestrator.py` remains the compatibility shell for lifecycle flow,
candidate production, recon/researcher prompt execution, continuation/recovery
branches, evidence selection, final-answer packet assembly, persistence, and
Author execution. These remain because AG-91H intentionally wires the first
spine only; AG-91I should extract query production behind RunKernel
actions/observations.

To keep the compatibility shell shrinking, Analyst quantitative packet helper
implementation moved mechanically into `core.analyst_quant_packet_runtime` while
`pipeline_orchestrator.py` re-exports the historical helper names used by tests
and callers. The prompt-adjacent packet section is covered by an exact string
guard in `tests/test_run_kernel_ag91h.py`.

## Closed Surfaces

This phase did not intentionally change prompt text, provider/depth policy,
query text/order policy, retrieval ranking/filtering, source-class recovery
query ownership, final evidence selection, citation eligibility, final-answer
prose/posture, persistence/cache behavior, live provider/model/search calls, or
secret/private artifact access.
