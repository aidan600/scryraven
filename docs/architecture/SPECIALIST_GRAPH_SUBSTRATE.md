# Specialist Graph Substrate

Status: current
Authority: canonical:specialist-graph-substrate
Default-read: no
Applies-to: generic Specialist proposals, registry resolution, execution policy, work, results, scheduling, and D-prime consumption
Does-not-authorize: product capability registration, calculator activation, provider or model calls, retrieval, recursion, parallel Specialist work, admission, FAP, Author, or live validation
Verified-against-runtime: 56b78b24015a75ff964b83ffcc77c4a18f24fb58
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
-> either one registered deterministic capability execution or a typed nonexecution disposition
-> immutable proposal disposition and optional result identity plus validator lifecycle
-> one `specialist_need_handoff` component or synthesis D-prime input
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
contract and graph refs, capability descriptor, exact RunKernel authorization
action, batch/lease lineage, and Specialist budget ref. It retains only the
bounded-input digest, input-schema ref, lineage refs, and reconstruction ref;
the component or synthesis input packet itself is not retained.
Grant, cancellation, dispatch, staleness, failure, blocked, contested, and
completion postures remain RunKernel-governed and terminally accounted.

## Disposition, Result, And Validator Lifecycle

Every terminal proposal receives an immutable sibling disposition. The
disposition preserves the original proposal digest, origin and exact target,
required/optional posture, capability and policy resolution, availability,
assumptions, caveats, nonclaims, and any typed nonexecution reason. Availability
postures are result available, unavailable by policy/capability/target/budget,
failed, blocked, or contested. Optional pool exhaustion creates no second
lease, adapter call, model call, or accounting unit; required exhaustion still
blocks the ordinary path.

A Specialist result contains only bounded output, assumptions, caveats,
blockers, confidence and execution posture, exact work/proposal/capability
lineage, and explicit zero-authority declarations. It has no component or
synthesis admission, SemanticObservation, ComponentCoverage, Sufficiency,
FinalAnswerPacket, Author, citation, or source-obligation authority.

Disposition and result identities are immutable. Validator-consumption fields
carry a separate lifecycle on the disposition, unified handoff, and any result:
pending, consumed by component D-prime, consumed by synthesis D-prime,
contested, or rejected. Stable refs and identity digests do not include that
mutable lifecycle.

Component and synthesis D-prime receive Specialist material only under the
single top-level `specialist_need_handoff` namespace. It carries either a
bounded result or the typed reason the proposed need was unavailable. Only the
absence of a proposal omits the handoff. Ordinary nominated claims, evidence,
component refs, graph refs, and admitted input refs remain unchanged. RunKernel
independently rederives the current D-prime role, action, artifact, target, and
exact handoff-bearing input digest before allowing exactly-once consumption;
caller-supplied route or validation status is not trusted.

## Scrutineer Boundary

S0 permits automatic remediation only for an exact current synthesis leaf.
The completed result is attached to that leaf, prior D-prime/admission
authority is cleared, and the graph requires fresh synthesis D-prime validation
and a fresh full Scrutineer pass. Component, edge, subgraph, graph, and
whole-case Scrutineer targets are retained as typed rejected or unsupported
proposals. They do not trigger structural rewrite, broad recomputation, or
silent fallback.

## Privacy And Authority Boundaries

Retained Specialist artifacts are bounded projections only. Immediately before
dispatch commitment, the driver reconstructs the exact component or synthesis
input from current canonical owners and verifies its digest. Reconstruction
failure cancels and refunds the exact reservation once, leaves zero Specialist
spent units, publishes no Specialist execution action, creates no result, and
never starts the adapter. Both optional and required proposals receive exactly
one failed disposition and unified handoff. The optional handoff remains visible
to D-prime and nonblocking. The required handoff remains pending and unconsumed
because D-prime does not run; Scheduler V3 reaches
`blocked_required_specialist_work` before the existing safe non-Author terminal.
The transient packet exists only in
driver-local execution scope. It is absent from RunKernel, scheduler
leases/batches/actions, the Specialist work plane, observations, graphs, logs,
and traces. Raw prompts,
raw model or provider payloads, private logs, full traces, database rows,
caches, secrets, and private artifacts are neither accepted nor retained.
Capability adapters stay in injected runtime scope and are not serialized into
RunKernel state.

The substrate grants no provider, model, search, fetch/read, retrieval, or
publication authority. It introduces no hidden fallback, recursive Specialist
proposal, parallel Specialist execution, or arbitrary-query support.

## Nonproofs

Offline tests prove generic contract reuse, exact lineage, ordinary bounded
consumption, closed defaults, typed rejection, and deterministic scheduling.
They do not prove a product Specialist, calculator activation, live correctness,
answer quality, broad capability coverage, arbitrary-query support, or useful
hosted/Local capacity.
