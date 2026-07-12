# Multi-Component Synthesis Runtime Architecture

Status: canonical repo-visible architecture for the installed bounded ordinary
multi-component runtime through Phase 5A hosted component parallel dispatch.

Mode: BUILD.

Phase: `AG-MULTICOMPONENT-HOSTED-COMPONENT-PARALLEL-DISPATCH-01`.

Verdict target: `YES`.

The earlier `MULTICOMPONENT-RUNTIME-ARCHITECTURE-DOCTRINE-REPAIR-01` established
the governing direction. Phase 1 installed the bounded ordinary product path
for `ordinary-bounded-multicomponent-factual-synthesis-v1`. Phase 2 installed
one governed missing-component recovery and AnswerContract amendment. Phase 3
replaces Phase 2's ordinary successful-recovery whole-graph rebuild with serial
selective invalidation, carry-forward, and affected-only recomputation. Phase 4
installs RunKernel-owned incremental scheduling and exact semantic-work leases
on the default selected ordinary path. Phase 5A upgrades that ordinary consumer
to Scheduler V2 and bounded hosted width-2 overlap for eligible initial
component Analyst and D-prime waves.

## Current, Reusable, And Target States

These three states are distinct and must not be collapsed.

### Current default ordinary behavior

Nonqualifying and single-component runs retain the established direct lane:

```text
accepted component structure
+ selected passages / sanitized content refs
+ EvidenceLedger facts
-> ordinary semantic producer
-> RunKernel commit_semantic_producer_bundle(...)
-> SemanticObservation
-> ComponentCoverage
-> ordinary RunAuthority Sufficiency
-> ordinary FinalAnswerPacket
-> ordinary Author
```

For the supported qualifying class, lane selection occurs before canonical
semantic production and bypasses that direct producer:

```text
accepted explicit factual component structure and synthesis directive
-> component Analyst
-> component D-prime
-> RunKernel component admission
-> SemanticObservation / ComponentCoverage
-> ComponentWorkNode V1
-> ComponentWorkGraph V1 and synthesis roles
-> ordinary Sufficiency / FinalAnswerPacket / Author
```

Broad or legacy Analyst prose is not relabeled typed component authority. The
two lanes are selected before semantic output; their results are never both run
and compared afterward.

### Existing reusable bounded capability

The repository already has bounded `AnalystFinding`, component D-prime,
same-component multi-source, recovery, source-obligation, citation-source, and
narrow Scrutineer-gate machinery in named product-status, dogfood, diagnostic,
or specialized lanes. It also has ComponentWorkGraph V0, proposal-only
cross-component Workbench, synthesis D-prime validation, RunKernel graph and
synthesis admission, and a serial checkpoint as bounded repo-visible contracts.

These are mature reuse candidates. Their presence does not prove that the
default ordinary semantic producer invokes the complete approved component
validation or cross-component synthesis lane. The V0 contracts and serial
checkpoint are not ordinary answer consumption.

### Installed Phase 1 through Phase 5A path

```text
component requirement and custody facts
-> typed regular component Analyst SmartModel proposal
-> component D-prime SmartModel validation
-> RunKernel component admission
-> SemanticObservation
-> ComponentCoverage
-> ComponentWorkNode

-> bounded ComponentWorkGraph V1
-> dedicated Cross-Component Analyst SmartModel proposal
-> dedicated synthesis D-prime SmartModel validation
-> full Scrutineer SmartModel challenge when required
-> RunKernel canonical graph/synthesis admission
-> ordinary RunAuthority Sufficiency
-> ordinary FinalAnswerPacket
-> ordinary Author
-> ordinary user-facing answer
```

Every semantic role arrow in that selected path is scheduler-governed. The
ordinary runtime asks RunKernel to derive and atomically grant the exact
contiguous next work batch, reconstructs every named packet on the main thread,
and asks RunKernel to atomically commit batch spend plus all ordered child
actions before transport. Transport-only outcomes are collected by canonical
batch index; role observations and deterministic consumers reduce serially in
child-action order. The driver does not receive a caller-authored role, logical
key, batch, width, backend class, or packet as its next-work choice. The
component Analyst, component D-prime, initial and selective Cross-Component
Analyst, initial and affected synthesis D-prime, and initial and fresh selective
Scrutineer calls all require the exact active lease lineage.

Scheduler V2 derives `hosted_api` width 2 for configured OpenAI and OpenRouter,
`local_openai_compatible` width 1 for Local, and `conservative_unknown` width 1
for unsupported identities through the existing canonical provider normalizer.
Only independent initial component Analyst and D-prime batches may contain two
items. Cross-Component Analyst, synthesis D-prime, Scrutineer, recovery, and
selective work remains serial. Scheduler V1 is retained as immutable historical
serial schema and cannot accept V2 batch or parallel state.

On one authorized missing-component recovery, the installed continuation is:

```text
authorization-bound pre-transition ComponentWorkGraph V1
-> RunKernel-derived affected synthesis closure
-> exact recovered component admission and current AnswerContract binding
-> affected synthesis staled; unaffected synthesis deterministically carried
-> selective Cross-Component Analyst proposal for affected keys only
-> affected synthesis D-prime and RunKernel admission in topological order
-> one fresh whole-case Scrutineer
-> ordinary Sufficiency / FinalAnswerPacket / Author
```

Carried nodes preserve semantic lineage but do not launder the prior D-prime or
admission as direct authority for a new node revision. Their current authority
is the RunKernel carry-forward action; the final node/graph binding is recorded
in a non-circular sibling carry-forward projection.

## Durable Role Ownership

| Role | Owns | Must not do |
| --- | --- | --- |
| Planner / semantic producer | Proposes query meaning, answer components, source/search requirements, and explicit structural request relationships. | Admit component or synthesis claims, validate its own proposals, or manufacture evidence. |
| Regular component Analyst | Uses a configured SmartModel to propose what bounded custodied evidence supports for one component. | Validate or admit its own proposal, dispatch recovery, or render an answer. |
| Component D-prime | Uses a separately configured SmartModel role to validate the component proposal against evidence, component, scope, source-obligation, currentness, and caveat refs. | Act as first-pass Analyst, invent the claim, admit it, dispatch search, or render. |
| Cross-Component Analyst | Uses a dedicated configured SmartModel role to propose semantic relationships, dependencies, contradictions, constraints, synthesis nodes, missing components, caveats, and recovery needs. | Validate or admit its own synthesis, dispatch recovery, or render. |
| Synthesis D-prime | Uses a separate configured SmartModel role to validate nominated synthesis against current admitted component, synthesis, edge, blocker, and caveat refs. | Invent synthesis, act as Cross-Component Analyst, admit state, or render. |
| Scrutineer | Uses a separate configured SmartModel role to adversarially challenge a component, synthesis, edge, subgraph, or whole-case posture. | Act as the first-pass Analyst, manufacture a replacement case, admit state, or render. |
| RunKernel | Derives current ready semantic work and transport profile; owns contiguous batches, atomic grants/cancellation/dispatch, child actions, exact leases, settlement, caps, and canonical reduction; and admits, blocks, challenges, or authorizes recovery. | Manufacture semantic output, replace semantic roles with deterministic heuristics, accept caller-authored scheduler/concurrency state, or become an orchestrator brain. |
| Sufficiency | Decides readiness from admitted state. | Invent or repair synthesis. |
| FinalAnswerPacket | Packages admitted and readiness-approved direct and synthesized material. | Generate, repair, validate, or reinterpret synthesis. |
| Author | Renders the packet and may explain admitted synthesis. | Create synthesis, glue unadmitted component outputs, repair evidence, or upgrade support. |

Durable mnemonic:

```text
D-prime verifies the claim.
Scrutineer attacks the case.
```

The existing narrow deterministic same-component multi-source Scrutineer gate
is not the full Scrutineer SmartModel role. It remains a reusable bounded gate,
not evidence that full cross-component scrutiny is installed.

The architecture configures role capabilities, not one hardcoded model. It
must not hardcode GPT-5.6 or any other runtime model. Deterministic code owns
schemas, cycle checks, identity/digest binding, budgets, safety, raw/private
hygiene, and output validation. Deterministic logic must not replace broad
semantic analysis, synthesis validation, or full scrutiny.

## Durable Graph Direction

The graph is n-capable, mode-budgeted, acyclic, serial-compatible initially,
and capable of bounded synthesis-of-synthesis. Two components are an example,
not a schema limit; one synthesis layer is not the durable architecture.

It has first-class concepts equivalent to:

```text
ComponentWorkNode
SynthesisWorkNode
```

`SynthesisWorkNode` is a preferred descriptive name, not a locked
implementation identifier. Whatever the final name, synthesis must be a
first-class identity-bearing, revision-bound, challengeable, admissible graph
object, not an external ref attached to a component node.

The graph supports:

- direct component results;
- subset synthesis and multiple independent synthesis groups;
- component-to-synthesis and synthesis-to-synthesis edges;
- bounded layered synthesis;
- node-, edge-, subgraph-, and whole-graph challenges.

Illustrative supported shape:

```text
A -> direct answer
B -> direct answer

C + D -> synthesis E
E + F -> synthesis S
```

Structural edges originate in planning and accepted request structure.
Cross-Component Analyst proposes semantic edges and changes in dependency
posture. Synthesis D-prime validates nominated semantic relations; RunKernel
alone admits them into canonical graph state. An empty edge set does not prove
semantic independence. Unknown or unassessed dependency posture must remain
explicit.

## AnswerContract Boundary

```text
AnswerContract component
= something the run owes the user

ComponentWorkNode
= governed lane for one answer obligation

SynthesisWorkNode
= subordinate derived reasoning needed to fulfill one or more obligations
```

A synthesis node does not automatically become an AnswerContract component.
The AnswerContract remains the run-level accountability overview; it is not the
graph and does not record every reasoning step. Admitted synthesis may become
FAP-safe user-facing answer material. Author may explain that admitted
synthesis but may not create it.

## ComponentWorkGraph V0 And V1

Do not silently redefine the established V0 contract.

`ComponentWorkGraph V1` is the installed bounded successor for the supported
ordinary class. It represents ComponentWorkNode refs, first-class
synthesis-node refs, structural edges, proposed and admitted semantic edges,
challenge refs, revision and staleness metadata, and depth/budget posture.

V0 may remain a compatibility input or review-only historical contract, but it
is an explicitly named strangler target for ordinary architecture. Phase 1
reuses its useful safety direction while leaving V0 unchanged and subordinating
ordinary qualifying consumption to V1.

## Phase 1 Envelope

Phase 1's named supported class is
`ordinary-bounded-multicomponent-factual-synthesis-v1`.

| Bound | Phase 1 value |
| --- | --- |
| Explicit component nodes | 2-5 |
| Maximum synthesis nodes | 4 |
| Maximum synthesis depth | 2 |
| Cross-Component Analyst rounds | 1 |
| Synthesis D-prime rounds | 1 per synthesis proposal |
| Scrutineer rounds | 1 when triggered |
| Automatic recovery rounds | 0 |
| Graph amendment rounds | 0 |

These are initial implementation bounds, not durable schema limits. Initial
relationships may include comparison, qualification, constraint, conditional
relationship, and applicability. Direct component output and synthesis may
coexist. Partial or blocked output is allowed when ordinary Sufficiency
authorizes it.

Full Scrutineer is required in Phase 1 when any of these is true:

- mode is Deep;
- a contradiction exists;
- an unresolved dependency exists;
- synthesis is materially caveated;
- high-stakes quantitative posture is detected by the ordinary economist safety
  telemetry;
- one synthesis node depends on another synthesis node;
- synthesis D-prime returns challenge, follow-up need, or ambiguous support.

Fast and Balanced may skip full Scrutineer only when no trigger applies.

## Ordinary Product Endpoint

Phase 1 reaches this one vertical product path:

```text
default ordinary entrypoint
-> typed component producer roles
-> component admission
-> graph and synthesis producer roles
-> RunKernel canonical graph/synthesis admission
-> ordinary RunAuthority Sufficiency
-> ordinary FinalAnswerPacket
-> ordinary Author
-> user-facing answer containing appropriate admitted synthesis
```

Graph admission alone is not product completion. Contracts, packets, fixtures,
tests, traces, status reports, serial checkpoints, diagnostic output, and
diagnostic finalization cannot substitute for ordinary answer consumption.
Sufficiency, FinalAnswerPacket, and Author must consume the admitted direct and
synthesized material through the default ordinary entrypoint in the same BUILD.

## Installed Phase 4, Phase 5A, And Later Commitments

Phases 1 through 4 establish serial correctness, ordinary end-to-end
consumption, one bounded dynamic recovery, selective recomputation, and
RunKernel-owned scheduling with work/budget leases. Phase 5A installs Scheduler
V2 and bounded hosted overlap through that same default selected ordinary path;
the old single-work role loops remain only historical compatibility helpers.
After every wave's role actions are terminal, the scheduler driver invokes the
existing deterministic graph, admission, recovery, closure, accounting, and
finalization owners serially; those owners do not nominate the next semantic
call.

Batch membership is a contiguous prefix of canonical ready-work order. The
grant reserves all exact leases atomically. Complete private child descriptors
are validated before mutation. Dispatch atomically spends the batch and
publishes all contiguous child-action sequences. A failed precommit batch
publishes no child action, consumes no logical key, and returns all reservations
together. After commitment, executor, submission, transport, output-validation,
artifact, and stale failures remain spent and drain all siblings before a
blocked terminal is installed.

Workers receive no RunKernel, mutable RunState, graph, EvidenceLedger, admission
state, recovery authority, FAP/Author state, persistence writer, or trace
writer. They execute synchronous transport and pure parsing/normalization only.
Canonical artifacts, digests, observations, lease settlement, component
admission, and graph changes are constructed on the main product thread.
Physical completion order cannot alter canonical reduction order.

The compatibility envelope is derived from the one existing shared role-cap
mapping (component Analyst 5, component D-prime 5, Cross 2, synthesis D-prime
8, Scrutineer 2). No permanent Fast/Balanced/Deep semantic-call budget values
were chosen. A predispatch cancellation returns its reservation exactly once;
postdispatch failure or stale-result rejection retains the spent unit. Required
work exhaustion reaches ordinary Sufficiency and FinalAnswerPacket, then the
installed safe non-Author terminal RunOutcome.

Completed and blocked scheduler projections require zero active physical
leases. Completion rejects either a granted reservation or a dispatch-committed
lease before checking readiness and leaves scheduler, lease, and budget state
unchanged. Lease invalidation is derived only inside the RunKernel reducers that
independently construct and install a canonical AnswerContract, Graph V1, target,
or selective-closure revision. The reducer tests the exact leased work against
its validated candidate state: affected granted work is cancelled and refunded
once; affected dispatch-committed work is marked stale while retaining its spent
unit and rejecting any late successful observation; unrelated work remains
active. No caller-authored transition label or digest can create cancellation
authority.

The current sequence is:

```text
Phase 4: RunKernel scheduling and work/budget leases
-> Phase 5A: hosted initial-component width-2 transport
-> later: separately licensed hosted characterization
-> later: calibrated Local characterization
```

Phase 5A is a compatibility cap, not a measurement of maximum useful provider
concurrency. Adaptive rate-limit handling, user-configurable width, live hosted
characterization, Local parallelism, graph-bound parallelism, and quantitative
Specialist activation are not installed. The durable graph remains
serial-compatible.

## Phase Boundary And Non-Proofs

Phase 5A proves through injected offline transports in ordinary `run_pipeline`
that eligible hosted initial component Analyst and D-prime calls physically
overlap at maximum in-flight count 2 while deterministic canonical state and the
ordinary answer remain stable. It proves Local/unknown width-1 compatibility,
atomic precommit behavior, failure draining, and exact accounting. It does not
prove live model quality, provider throughput/rate-limit capacity,
arbitrary-query support, more than one recovery/selective round, permanent mode
budgets, Local parallelism, or graph-bound parallelism.
