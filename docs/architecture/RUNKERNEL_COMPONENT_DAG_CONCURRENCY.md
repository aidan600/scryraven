# RunKernel Component DAG And Concurrency

Status: graph, scheduling, and concurrency companion doctrine. The canonical
multi-component role and synthesis architecture is
[MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md](MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md).

Mode: BUILD.

Current cross-component doctrine:
[CROSS_COMPONENT_ANALYST_WORKBENCH.md](CROSS_COMPONENT_ANALYST_WORKBENCH.md).

## Purpose

Future multi-component and multi-hop work should be represented as a
RunKernel-owned component dependency graph with compact component refs and
explicit admission boundaries, not a sequential checklist.

The durable direction is an n-capable, mode-budgeted, acyclic graph that is
serial-compatible initially and supports bounded synthesis-of-synthesis.
Serial correctness, dynamic recovery, selective recomputation, and Phase 4
RunKernel scheduling/work leases are installed on ComponentWorkGraph V1.
Runtime parallelism remains a later commitment. None of execution, scheduling,
budget leases, or runtime parallelism is installed by the historical V0
contracts.

The installed implementation is owned by `core.multicomponent_graph_scheduling`
and consumed by the ordinary selected runtime. This companion document does not
itself execute work, route models, plan queries, or plan semantics.

## Multi-Source And Multi-Component

Multi-source means one answer component with multiple sources bearing on that
component.

Multi-component means one user question with multiple answer components. Each
component may require its own searches, sources, analysis, assumptions, and
synthesis.

Do not call multi-component work "multi-source." A one-component multi-source
posture does not prove multi-component aggregation, dependency handling, or
concurrency safety.

## Dependency Graph Doctrine

Multi-component work should be a dependency graph, not a checklist.

Future shape:

```text
user question
-> planner proposes component graph
-> RunKernel authorizes graph/scheduling/budget leases
-> independent nodes may run concurrently when dependencies are satisfied
-> dependent nodes wait for inputs
-> Cross-Component Analyst Workbench proposes synthesis/dependency/gap posture
-> synthesis D-prime validates synthesis support over component refs
-> RunKernel admits / blocks / challenges / authorizes bounded recovery
-> later Sufficiency/FAP/Author phases consume only admitted refs
```

The next BUILD must go further than that historical intermediate shape:
ordinary Sufficiency, FinalAnswerPacket, Author, and user-facing answer output
must consume appropriate admitted direct and synthesized material in the same
end-to-end product path. Graph admission or a serial checkpoint alone is not
product completion.

Planner and Analyst surfaces may propose decomposition. RunKernel owns
scheduling, budget leases, caps, custody, cancellation, and admission. Analyst
must not directly launch parallel work. Concurrency must preserve authority, not
bypass it.

The unsafe path remains closed:

```text
component A final
+ component B final
+ component C final
-> Author glues
```

## Future ComponentWorkNode Contract Shape

`ComponentWorkNode` V0 now exists as a typed projection over one current product
component lane. It is not graph execution, scheduler authorization,
multi-component planning, budget leasing, FAP, Author, citation rendering, or
product correctness.

A future graph-level node shape may include:

- `node_id`
- `parent_run_id`
- `component_id`
- `component_type`
- `dependency_ids`
- search requirements
- source obligation requirements
- source authority posture requirements
- assigned role/lane
- model role requirement if any
- budget lease
- status
- output packet refs
- blocker refs
- caveats/nonclaims
- raw/private retention flags

These fields should remain authority-preserving. They should not become a
shadow planner, shadow product path, or prompt-visible substitute for RunKernel
authorization.

## Component And Synthesis Nodes

The durable graph has first-class concepts equivalent to `ComponentWorkNode`
and `SynthesisWorkNode`. The exact synthesis-node implementation name remains
open, but synthesis must be identity-bearing, revision-bound, challengeable,
and admissible. It must not remain only an external reference attached to a
component node.

The graph supports direct component results, subset synthesis, multiple
independent synthesis groups, component-to-synthesis edges,
synthesis-to-synthesis edges, bounded layered synthesis, and node-, edge-,
subgraph-, and whole-graph challenges. An empty edge set means no admitted edge
is present; it does not prove semantic independence. Unknown or unassessed
dependency posture must remain explicit.

`ComponentWorkGraph V1` is the preferred successor. It should represent
component refs, first-class synthesis-node refs, structural edges, proposed and
admitted semantic edges, challenge refs, revision/staleness metadata, and
depth/budget posture. Do not silently redefine V0: V0 may remain a compatibility
or review-only input and is a named strangler target for the ordinary path.

## Installed Phase 4 Budget And Lease Doctrine

The selected ordinary ComponentWorkGraph V1 path uses a parent compatibility
envelope plus exact semantic-work leases.

Component budgets must be reserved from the parent envelope before concurrent
work starts. This prevents multi-component work from silently multiplying cost,
latency, provider calls, model calls, fetch/read attempts, or retrieval work.

The parent total is derived from the shared installed role caps rather than a
second caller-authored total. One semantic transport commits one unit. Grant
moves remaining to reserved; predispatch cancellation returns it exactly once;
dispatch moves reserved to permanently spent. Completion and postdispatch
failure do not change allocation. Returned units are cumulative audit, not a
fourth live bucket.

Leases are cancellable before dispatch, bounded, attributable to exact current
work, and auditable by RunKernel. Failed or stale postdispatch work retains its
unit. Required exhaustion reaches ordinary Sufficiency/FAP and the safe blocked
terminal. Phase 4 permits one active physical lease; logical readiness is not
physical concurrency.

## Mode Doctrine

Fast uses low width and low depth, minimal recovery, small concurrency, and a
strong speed/boundedness posture.

Balanced uses moderate width, limited depth, concurrent independent components
when dependencies are satisfied, and one final aggregation pass.

Deep / Pro uses a larger graph, more specialist lanes/source classes,
aggregation, recovery, and higher budgets. Larger budget does not change
semantic authority.

## Cross-Component Analyst Workbench

Component success is not final answer authority.

Cross-Component Analyst Workbench is the proposal-only synthesis layer between
per-component lanes and synthesis D-prime validation. It must review:

- all component outputs;
- conflicts;
- assumptions;
- missing dependencies;
- normalization assumptions;
- source-authority postures;
- caveats and nonclaims;
- whether synthesis is allowed;
- whether answer should block.

It may propose synthesis, dependency, missing-component, contradiction, caveat,
and recovery refs. It must not validate its own synthesis, admit evidence,
dispatch search, collapse component refs into untraceable summary, create a
parallel Analyst system, or feed Author directly.

Only after Cross-Component Analyst proposal, synthesis D-prime validation, and
RunKernel admission may later phases consider Sufficiency/FAP/Author
consumption.

## Model-Role Routing Pointer

Do not design around one blanket model.

RunKernel itself should not become an LLM thinker. If an LLM is needed for
planning or interpretation, it should be a Planner, Analyst, or Specialist call
authorized and recorded by RunKernel.

Keep `COMPONENT-MODEL-ROLE-ROUTING-MATRIX-01` pinned as future work.

## Near-Term Planning Constraint

`GENERIC-QUERY-TO-RELATION-PLANNING-01` adds a no-live single-relation planning
dry run, but it does not implement multi-component planning.

Its single-relation plan packets carry metadata candidates shaped so they can
later lift into `ComponentWorkNode` / `ComponentWorkGraph` concepts. Those
candidates are not implemented nodes, scheduling authorization, or budget
leases. Do not hardcode the assumption that ScryRaven will remain
single-component forever.

`GENERIC-SINGLE-RELATION-LIVE-DOGFOOD-01` may consume those same plan-derived
metadata candidates while running one default-off live dogfood relation under
explicit confirmation and caps. That consumption does not implement
`ComponentWorkNode`, `ComponentWorkGraph`, RunKernel DAG scheduling, concurrency,
or budget leases, and it must remain single-relation only.

## Historical V0 Sequence And Current Roadmap

These are future doctrine items, with the currently introduced contract noted
where it exists:

- `COMPONENT-MODEL-ROLE-ROUTING-MATRIX-01`
- `FAP-AUTHOR-BOUNDARY-INSPECTION-01`
- `RUN-KERNEL-COMPONENT-DAG-AND-CONCURRENCY-BUDGET-01`
- `MULTI-COMPONENT-QUERY-PLANNING-01`
- `COMPONENTWORKGRAPH-V0-NOEXEC-CONTRACT-01`
- `CROSS-COMPONENT-SYNTHESIS-PROPOSAL-V0-01`
- `DPRIME-SYNTHESIS-VALIDATION-V0-01` - introduced as a validation-only
  `core.dprime_synthesis_validation` contract over Workbench proposal refs.
- `RUNKERNEL-COMPONENT-GRAPH-ADMISSION-V0-01` - introduced as a ref-only
  `core.runkernel_component_graph_admission` contract over ComponentWorkGraph,
  Workbench, and synthesis D-prime validation refs.
- `MULTICOMPONENT-SERIAL-DRY-RUN-PLANNING-CHECKPOINT-01` - introduced as a
  review-only serial dry-run checkpoint in
  `core.multicomponent_serial_dry_run_checkpoint` over graph, Workbench,
  synthesis D-prime validation, and RunKernel admission refs.
- `MULTI-COMPONENT-LIVE-DOGFOOD-01`

The list above records V0 provenance and older roadmap names; it is not the
current next-phase route. Phases 1 through 4 are installed. The recommended next
checkpoint is Phase 5 bounded physical dispatch parallelism through the same
scheduler.

After serial end-to-end ordinary activation, the committed Boundary 3 sequence
is dynamic graph and AnswerContract amendment, targeted ordinary research
re-entry, selective invalidation, selective synthesis recomputation,
revision-specific validation/scrutiny, and RunKernel scheduling and budget
leases are installed. Runtime parallelism where supported remains deferred, not
rejected.

## Current Status

The V0 work through
`MULTICOMPONENT-SERIAL-DRY-RUN-PLANNING-CHECKPOINT-01` remains no-execution and
review-only. ComponentWorkGraph V1 now supports the installed Phase 1 ordinary
path, Phase 2 recovery, Phase 3 selective recomputation, and Phase 4 serial
scheduling/lease authority through ordinary Sufficiency/FAP/Author consumption.
It does not install runtime parallelism, live validation, source-display
changes, citation changes, or product correctness claims. No permanent
Fast/Balanced/Deep semantic-call budgets were selected.

ScryRaven is not friend-level MVP and is not a general supported-query MVP.

Related current posture docs:

- [CROSS_COMPONENT_ANALYST_WORKBENCH.md](CROSS_COMPONENT_ANALYST_WORKBENCH.md)
- [MVP_SUPPORTED_QUERY_CLASS_BOUNDARY.md](MVP_SUPPORTED_QUERY_CLASS_BOUNDARY.md)
- [SOURCE_AUTHORITY_POSTURE.md](SOURCE_AUTHORITY_POSTURE.md)
- [AG96C0_MODE_CONTRACT_COMPONENT_BUDGET_DOCTRINE.md](AG96C0_MODE_CONTRACT_COMPONENT_BUDGET_DOCTRINE.md)
- [DPRIME_ARCHITECTURE.md](DPRIME_ARCHITECTURE.md)
- [RUN_CONTRACT_SEMANTIC_LOOP.md](RUN_CONTRACT_SEMANTIC_LOOP.md)
