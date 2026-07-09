# RunKernel Component DAG And Concurrency

Status: architecture doctrine only for future multi-component work.

Mode: BUILD.

Current cross-component doctrine:
[CROSS_COMPONENT_ANALYST_WORKBENCH.md](CROSS_COMPONENT_ANALYST_WORKBENCH.md).

## Purpose

Future multi-component and multi-hop work should be represented as a
RunKernel-owned component dependency graph with compact component refs and
explicit admission boundaries, not a sequential checklist.

This document does not implement component DAG scheduling, budget leases, model
routing, query planning, or multi-component planning.

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

## Budget Doctrine

Future component DAG work should use a parent run budget plus component budget
leases.

Component budgets must be reserved from the parent envelope before concurrent
work starts. This prevents multi-component work from silently multiplying cost,
latency, provider calls, model calls, fetch/read attempts, or retrieval work.

Budget leases should be cancellable, bounded, attributable to component work,
and auditable by the parent run. Unused budget may return to the parent envelope
only through RunKernel policy.

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

## Future Roadmap Pointer

These are future doctrine items, not active implementation in this phase:

- `COMPONENT-MODEL-ROLE-ROUTING-MATRIX-01`
- `FAP-AUTHOR-BOUNDARY-INSPECTION-01`
- `RUN-KERNEL-COMPONENT-DAG-AND-CONCURRENCY-BUDGET-01`
- `MULTI-COMPONENT-QUERY-PLANNING-01`
- `COMPONENTWORKGRAPH-V0-NOEXEC-CONTRACT-01`
- `CROSS-COMPONENT-SYNTHESIS-PROPOSAL-V0-01`
- `DPRIME-SYNTHESIS-VALIDATION-V0-01`
- `RUNKERNEL-COMPONENT-GRAPH-ADMISSION-V0-01`
- `MULTI-COMPONENT-LIVE-DOGFOOD-01`

## Current Status

This phase is documentation-only. It does not open query-to-relation planning,
multi-component planning, RunKernel DAG scheduling, budget lease implementation,
model routing, FAP redesign, Author behavior, live dogfood behavior, or product
correctness claims.

ScryRaven is not friend-level MVP and is not a general supported-query MVP.

Related current posture docs:

- [CROSS_COMPONENT_ANALYST_WORKBENCH.md](CROSS_COMPONENT_ANALYST_WORKBENCH.md)
- [MVP_SUPPORTED_QUERY_CLASS_BOUNDARY.md](MVP_SUPPORTED_QUERY_CLASS_BOUNDARY.md)
- [SOURCE_AUTHORITY_POSTURE.md](SOURCE_AUTHORITY_POSTURE.md)
- [AG96C0_MODE_CONTRACT_COMPONENT_BUDGET_DOCTRINE.md](AG96C0_MODE_CONTRACT_COMPONENT_BUDGET_DOCTRINE.md)
- [DPRIME_ARCHITECTURE.md](DPRIME_ARCHITECTURE.md)
- [RUN_CONTRACT_SEMANTIC_LOOP.md](RUN_CONTRACT_SEMANTIC_LOOP.md)
