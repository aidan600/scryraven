# Multi-Component Synthesis Runtime Architecture

Status: canonical repo-visible architecture for the installed bounded ordinary
multi-component runtime and its deferred dynamic-graph direction.

Mode: BUILD.

Phase: `AG-MULTICOMPONENT-ORDINARY-END-TO-END-SYNTHESIS-01`.

Verdict target: `YES`.

The earlier `MULTICOMPONENT-RUNTIME-ARCHITECTURE-DOCTRINE-REPAIR-01` established
the governing direction. Phase 1 now installs the bounded ordinary product path
for `ordinary-bounded-multicomponent-factual-synthesis-v1`. The recommended
next phase is `AG-MULTICOMPONENT-DYNAMIC-GRAPH-RECOVERY-01`.

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

### Installed Phase 1 path

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

This complete bounded target is installed for the named supported query class.
It is not a claim of arbitrary-query support or dynamic graph recovery.

## Durable Role Ownership

| Role | Owns | Must not do |
| --- | --- | --- |
| Planner / semantic producer | Proposes query meaning, answer components, source/search requirements, and explicit structural request relationships. | Admit component or synthesis claims, validate its own proposals, or manufacture evidence. |
| Regular component Analyst | Uses a configured SmartModel to propose what bounded custodied evidence supports for one component. | Validate or admit its own proposal, dispatch recovery, or render an answer. |
| Component D-prime | Uses a separately configured SmartModel role to validate the component proposal against evidence, component, scope, source-obligation, currentness, and caveat refs. | Act as first-pass Analyst, invent the claim, admit it, dispatch search, or render. |
| Cross-Component Analyst | Uses a dedicated configured SmartModel role to propose semantic relationships, dependencies, contradictions, constraints, synthesis nodes, missing components, caveats, and recovery needs. | Validate or admit its own synthesis, dispatch recovery, or render. |
| Synthesis D-prime | Uses a separate configured SmartModel role to validate nominated synthesis against current admitted component, synthesis, edge, blocker, and caveat refs. | Invent synthesis, act as Cross-Component Analyst, admit state, or render. |
| Scrutineer | Uses a separate configured SmartModel role to adversarially challenge a component, synthesis, edge, subgraph, or whole-case posture. | Act as the first-pass Analyst, manufacture a replacement case, admit state, or render. |
| RunKernel | Authorizes role calls, enforces caps, validates bindings, reduces canonical state, and admits, blocks, challenges, or authorizes recovery. | Manufacture semantic output, replace semantic roles with deterministic heuristics, or become an orchestrator brain. |
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
- high-stakes posture is detected;
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

## Boundary 3 And Later Commitments

Phase 1 establishes serial correctness and ordinary end-to-end consumption.
The committed later destination is:

```text
dynamic graph and AnswerContract amendment
-> targeted ordinary research re-entry
-> selective invalidation
-> selective synthesis recomputation
-> revision-specific validation and scrutiny
-> RunKernel scheduling and budget leases
-> runtime parallelism where supported
```

These Boundary 3 capabilities are deferred, not rejected or optional ideas.
Runtime parallelism is not currently installed and must not be claimed before
scheduling, leases, dependency readiness, cancellation, and resource support
are licensed. The durable graph remains serial-compatible even after supported
parallelism is added.

## Phase Boundary And Non-Proofs

Phase 1 proves an offline synthetic ordinary product path through RunOutcome and
CLI rendering. It does not prove live model quality, product correctness,
automatic graph recovery, automatic missing-component research, dynamic graph
mutation, selective recomputation, scheduling, budget leases, runtime
parallelism, or arbitrary-query support. Its caps are implementation bounds,
not permanent mode policy.

The recommended next checkpoint is exactly
`AG-MULTICOMPONENT-DYNAMIC-GRAPH-RECOVERY-01`.
