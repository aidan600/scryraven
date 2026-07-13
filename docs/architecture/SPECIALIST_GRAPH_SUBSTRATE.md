# Specialist Graph Substrate

Status: current
Authority: canonical:specialist-graph-substrate
Default-read: no
Applies-to: generic Specialist proposals, registry resolution, execution policy, work, results, scheduling, and D-prime consumption
Does-not-authorize: product capability registration, calculator activation, provider or model calls, retrieval, recursion, parallel Specialist work, admission, FAP, Author, or live validation
Verified-against-runtime: 46f4fc998f1aae338aff24e9a7033f32ee90c78a
Update-trigger: merged change to Specialist proposal, registry, policy, work, result, scheduling, or validator-consumption contracts

## Responsibility

This document owns the installed generic Specialist graph substrate. Installed
state is summarized in [ScryRaven Current State](SCRYRAVEN_CURRENT_STATE.md),
phase order belongs to [Current Roadmap](../roadmap/CURRENT_ROADMAP.md), and the
ordinary bounded consumer belongs to
[Multi-Component Synthesis Runtime Architecture](MULTICOMPONENT_SYNTHESIS_RUNTIME_ARCHITECTURE.md).

The substrate lets an existing semantic role propose a bounded need, lets
RunKernel bind that proposal to exact current authority, resolves an explicitly
registered deterministic capability under an injected execution policy, runs
one governed work item, and routes its bounded result through the appropriate
D-prime input. It does not make a Specialist result admitted truth.

## Installed Contract

The installed sequence is:

```text
role artifact with optional Specialist need proposal
-> RunKernel proposal normalization and current-target binding
-> registry resolution plus execution-policy decision
-> Scheduler V3 Specialist lease in a separate compatibility pool
-> one registered deterministic capability execution
-> immutable Specialist result identity plus validator lifecycle
-> namespaced component or synthesis D-prime input
-> ordinary RunKernel graph/admission flow
```

Component Analyst, Cross-Component Analyst, and full Scrutineer may emit the
same optional proposal shape. A proposal names a bounded question, capability
requirement, optional capability hint, exact target, input/output schema refs,
input artifact refs, assumptions, caveats, nonclaims, advisory budget posture,
and a nonrecursive parent posture.

RunKernel binds the proposal to the originating completed role action and
artifact, current AnswerContract, current component or graph target revision,
registry digest, and execution-policy digest. Caller-supplied authority cannot
replace these canonical bindings.

## Registry And Execution Policy

The registry is capability-generic. Each descriptor has a stable capability
ID, version, requirement, input/output schema refs, deterministic resource and
executor classes, and a descriptor digest. A candidate capability hint is
advisory; resolution deterministically selects from compatible enabled
descriptors under policy. Unknown, disabled, or schema-incompatible
capabilities fail closed with a typed proposal posture.

The default registry and default execution policy are closed. No product
capability is registered or enabled by S0. Tests inject two inert deterministic
capabilities to prove reuse without adding driver branches. The existing
source-bound calculator remains unchanged and is not registered by this phase.

## Scheduler V3 And Budget Separation

Scheduler V3 is an upgrade of the existing RunKernel scheduler and is selected
only when both a Specialist registry and execution policy are injected into an
ordinary bounded run. Runs without that injection retain Scheduler V2 behavior.

Specialist work uses its own compatibility pool:

- limit `0` or `1` per run;
- serial, main-thread execution only;
- maximum one in flight;
- no recursion;
- no provider transport or model request;
- no token or model-cost accounting;
- no consumption of the five semantic role caps or their 22-unit envelope.

The Specialist work node binds the accepted proposal, canonical target,
contract and graph refs, capability descriptor, bounded input digest, exact
RunKernel authorization action, batch/lease lineage, and Specialist budget ref.
Grant, cancellation, dispatch, staleness, failure, blocked, contested, and
completion postures remain RunKernel-governed and terminally accounted.

## Result And Validator Lifecycle

A Specialist result contains only bounded output, assumptions, caveats,
blockers, confidence and execution posture, exact work/proposal/capability
lineage, and explicit zero-authority declarations. It has no component or
synthesis admission, SemanticObservation, ComponentCoverage, Sufficiency,
FinalAnswerPacket, Author, citation, or source-obligation authority.

Result identity is immutable. Validator-consumption fields carry a separate
lifecycle on the retained work-plane record: pending, consumed by component
D-prime, consumed by synthesis D-prime, contested, or rejected. Stable result
refs and the result digest do not include that mutable lifecycle.

Component and synthesis D-prime receive Specialist material only under the
separate `specialist_result_inputs` namespace. Ordinary nominated claims,
evidence, component refs, graph refs, and admitted input refs remain unchanged.
D-prime still validates the semantic proposal, and RunKernel still owns every
admission or block.

## Scrutineer Boundary

S0 permits automatic remediation only for an exact current synthesis leaf.
The completed result is attached to that leaf, prior D-prime/admission
authority is cleared, and the graph requires fresh synthesis D-prime validation
and a fresh full Scrutineer pass. Component, edge, subgraph, graph, and
whole-case Scrutineer targets are retained as typed rejected or unsupported
proposals. They do not trigger structural rewrite, broad recomputation, or
silent fallback.

## Privacy And Authority Boundaries

Retained Specialist artifacts are bounded projections only. Raw prompts, raw
model or provider payloads, private logs, full traces, database rows, caches,
secrets, and private artifacts are neither accepted nor retained. Capability
adapters stay in injected runtime scope and are not serialized into RunKernel
state.

The substrate grants no provider, model, search, fetch/read, retrieval, or
publication authority. It introduces no hidden fallback, recursive Specialist
proposal, parallel Specialist execution, or arbitrary-query support.

## Nonproofs

Offline tests prove generic contract reuse, exact lineage, ordinary bounded
consumption, closed defaults, typed rejection, and deterministic scheduling.
They do not prove a product Specialist, calculator activation, live correctness,
answer quality, broad capability coverage, arbitrary-query support, or useful
hosted/Local capacity.
