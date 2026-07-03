# RunKernel Component DAG And Concurrency

Status: architecture doctrine only for future multi-component work.

Mode: BUILD.

## Purpose

Future multi-component and multi-hop work should be represented as a
RunKernel-owned component dependency graph with budget leases, not a sequential
checklist.

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
-> final Analyst aggregation reviews component packets
-> RunKernel admits / blocks / challenges
-> FAP packages authorized output
-> Author renders
```

Planner and Analyst surfaces may propose decomposition. RunKernel owns
scheduling, budget leases, caps, custody, cancellation, and admission. Analyst
must not directly launch parallel work. Concurrency must preserve authority, not
bypass it.

## Future ComponentWorkNode Contract Shape

`ComponentWorkNode` is a future contract shape, not a current implementation.
A future node may include:

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

## Final Analyst Aggregation

Component success is not final answer authority.

Final Analyst aggregation must review:

- all component outputs;
- conflicts;
- assumptions;
- missing dependencies;
- normalization assumptions;
- source-authority postures;
- caveats and nonclaims;
- whether synthesis is allowed;
- whether answer should block.

Only after final aggregation and RunKernel admission may FAP package authorized
multi-component output for Author rendering.

## Model-Role Routing Pointer

Do not design around one blanket model.

RunKernel itself should not become an LLM thinker. If an LLM is needed for
planning or interpretation, it should be a Planner, Analyst, or Specialist call
authorized and recorded by RunKernel.

Keep `COMPONENT-MODEL-ROLE-ROUTING-MATRIX-01` pinned as future work.

## Near-Term Planning Constraint

`GENERIC-QUERY-TO-RELATION-PLANNING-01` should not implement multi-component
planning yet.

Its single-relation plan packets should still be shaped so they can later lift
into `ComponentWorkNode` / `ComponentWorkGraph` concepts. Do not hardcode the
assumption that ScryRaven will remain single-component forever.

## Future Roadmap Pointer

These are future doctrine items, not active implementation in this phase:

- `COMPONENT-MODEL-ROLE-ROUTING-MATRIX-01`
- `FAP-AUTHOR-BOUNDARY-INSPECTION-01`
- `RUN-KERNEL-COMPONENT-DAG-AND-CONCURRENCY-BUDGET-01`
- `MULTI-COMPONENT-QUERY-PLANNING-01`
- `FINAL-ANALYST-AGGREGATION-PACKET-01`
- `MULTI-COMPONENT-LIVE-DOGFOOD-01`

## Current Status

This phase is documentation-only. It does not open query-to-relation planning,
multi-component planning, RunKernel DAG scheduling, budget lease implementation,
model routing, FAP redesign, Author behavior, live dogfood behavior, or product
correctness claims.

ScryRaven is not friend-level MVP and is not a general supported-query MVP.

Related current posture docs:

- [MVP_SUPPORTED_QUERY_CLASS_BOUNDARY.md](MVP_SUPPORTED_QUERY_CLASS_BOUNDARY.md)
- [SOURCE_AUTHORITY_POSTURE.md](SOURCE_AUTHORITY_POSTURE.md)
- [AG96C0_MODE_CONTRACT_COMPONENT_BUDGET_DOCTRINE.md](AG96C0_MODE_CONTRACT_COMPONENT_BUDGET_DOCTRINE.md)
- [DPRIME_ARCHITECTURE.md](DPRIME_ARCHITECTURE.md)
- [RUN_CONTRACT_SEMANTIC_LOOP.md](RUN_CONTRACT_SEMANTIC_LOOP.md)
